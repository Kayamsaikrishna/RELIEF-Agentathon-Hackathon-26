import pytest
from fastapi.testclient import TestClient
from PIL import Image

from relief.app import auth
from relief.app.api import create_app
from tests.conftest import make_case

PW = "Str0ngPassw0rd"


@pytest.fixture()
def app(settings):
    a = create_app(settings, llm=None, start_scheduler=False)
    db = a.state.db
    db.add_user("admin@example.org", "Admin One", "admin", auth.hash_password(PW))
    db.add_user("fac1@example.org", "Facilitator One", "facilitator", auth.hash_password(PW))
    db.add_user("fac2@example.org", "Facilitator Two", "facilitator", auth.hash_password(PW))
    return a


@pytest.fixture()
def client(app):
    return TestClient(app)


def login(client, email, pw=PW):
    r = client.post("/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def body(**kw):
    return make_case(**kw).model_dump(mode="json", exclude_none=True)


def test_health_is_public_and_minimal(client):
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["registry_synthetic"] is True and "model" not in h


def test_login_rules(client):
    assert client.get("/api/cases").status_code == 401
    assert client.post("/api/auth/login", json={"email": "admin@example.org", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "nobody@example.org", "password": PW}).status_code == 401
    h = login(client, "ADMIN@example.org")
    assert client.get("/api/auth/me", headers=h).json()["role"] == "admin"
    assert client.get("/api/cases", headers={"Authorization": "Bearer junk"}).status_code == 401


def test_login_throttle(client):
    for _ in range(5):
        client.post("/api/auth/login", json={"email": "fac1@example.org", "password": "bad"})
    assert client.post("/api/auth/login", json={"email": "fac1@example.org", "password": PW}).status_code == 429


def test_full_flow(client):
    h = login(client, "fac1@example.org")
    r = client.post("/api/cases", json=body(case_id="P1", referral={"present": "no"}), headers=h)
    assert r.status_code == 202
    res = client.get("/api/cases/P1", headers=h).json()  # background task has finished inside the test client
    assert res["status"] == "awaiting_approval" and res["findings"][0]["blocker"] == "REFERRAL" and res["meta"]["created_by"] == "fac1@example.org"
    assert client.post("/api/cases", json=body(case_id="P1"), headers=h).status_code == 409
    d = client.post("/api/cases/P1/decision", json={"action": "approve", "decided_by": "someone else"}, headers=h).json()
    assert d["status"] == "completed" and "Facilitator One" in d["decisions"][0]["decided_by"]  # the server sets the name, not the client
    log = client.get("/api/cases/P1/log", headers=h).json()
    assert log["decisions"][0]["action"] == "approve" and any(a["action"] == "case.approve" for a in log["audit"])
    assert client.get("/api/reminders", headers=h).json()[0]["case_id"] == "P1"
    assert client.get("/api/stats", headers=h).json()["by_status"]["completed"] == 1
    assert client.post("/api/cases/P1/decision", json={"action": "approve"}, headers=h).status_code == 409


def test_cases_are_private_to_their_owner_and_visible_to_admin(client):
    h1, h2, ha = login(client, "fac1@example.org"), login(client, "fac2@example.org"), login(client, "admin@example.org")
    client.post("/api/cases", json=body(case_id="O1", referral={"present": "no"}), headers=h1)
    assert client.get("/api/cases/O1", headers=h2).status_code == 404
    assert client.post("/api/cases/O1/decision", json={"action": "approve"}, headers=h2).status_code == 404
    assert client.get("/api/cases", headers=h2).json() == []
    assert len(client.get("/api/cases", headers=ha).json()) == 1
    assert client.get("/api/cases/O1", headers=ha).status_code == 200


def test_validation_and_not_found(client):
    h = login(client, "fac1@example.org")
    assert client.post("/api/cases", json=body(case_id="P2", hospital_id="H-404"), headers=h).status_code == 422
    assert client.post("/api/cases", json=body(case_id="P3", procedure_code="NOPE"), headers=h).status_code == 422
    assert client.post("/api/cases", json={"case_id": "x"}, headers=h).status_code == 422
    assert client.get("/api/cases/nothing", headers=h).status_code == 404
    assert client.post("/api/cases/P9/decision", json={"action": "edit"}, headers=h).status_code == 422


def test_document_path_must_come_from_uploads(client):
    h = login(client, "fac1@example.org")
    b = body(case_id="P4")
    b["documents"] = [{"doc_id": "D1", "kind": "card", "path": "/etc/passwd"}]
    assert client.post("/api/cases", json=b, headers=h).status_code == 422


def test_upload_checks(client, tmp_path):
    h = login(client, "fac1@example.org")
    p = tmp_path / "x.png"
    Image.new("L", (50, 50), 255).save(p)
    ok = client.post("/api/uploads", files={"file": ("x.png", p.read_bytes())}, headers=h)
    assert ok.status_code == 200
    assert client.post("/api/uploads", files={"file": ("x.exe", b"MZ")}, headers=h).status_code == 415
    assert client.post("/api/uploads", files={"file": ("x.png", b"not an image")}, headers=h).status_code == 415
    assert client.post("/api/uploads", files={"file": ("x.png", p.read_bytes())}).status_code == 401
    b = body(case_id="P5")
    b["documents"] = [{"doc_id": "D1", "kind": "card", "path": ok.json()["path"]}]
    assert client.post("/api/cases", json=b, headers=h).status_code == 202


def test_admin_user_management(client):
    ha, hf = login(client, "admin@example.org"), login(client, "fac1@example.org")
    assert client.get("/api/admin/users", headers=hf).status_code == 403
    assert client.get("/api/admin/system", headers=hf).status_code == 403
    new = {"email": "new@example.org", "name": "New Person", "role": "facilitator", "password": PW}
    assert client.post("/api/admin/users", json=new, headers=ha).status_code == 201
    assert client.post("/api/admin/users", json=new, headers=ha).status_code == 409
    assert client.post("/api/admin/users", json={**new, "email": "b@example.org", "password": "short"}, headers=ha).status_code == 422
    uid = [u for u in client.get("/api/admin/users", headers=ha).json() if u["email"] == "new@example.org"][0]["id"]
    assert client.patch(f"/api/admin/users/{uid}", json={"active": False}, headers=ha).status_code == 200
    assert client.post("/api/auth/login", json={"email": "new@example.org", "password": PW}).status_code == 401
    me = client.get("/api/auth/me", headers=ha).json()["id"]
    assert client.patch(f"/api/admin/users/{me}", json={"role": "facilitator"}, headers=ha).status_code == 409  # last admin
    assert client.get("/api/admin/audit", headers=ha).json()[0]["action"]
    assert len(client.get("/api/admin/rules", headers=ha).json()) == 31
    s = client.get("/api/admin/system", headers=ha).json()
    assert s["rules"] == 31 and s["model_ok"] is False and s["registry_synthetic"] is True


def test_change_password(client):
    h = login(client, "fac1@example.org")
    assert client.post("/api/auth/password", json={"current": "bad", "new": "NewPassw0rd123"}, headers=h).status_code == 400
    assert client.post("/api/auth/password", json={"current": PW, "new": "weak"}, headers=h).status_code == 422
    assert client.post("/api/auth/password", json={"current": PW, "new": "NewPassw0rd123"}, headers=h).status_code == 200
    login(client, "fac1@example.org", "NewPassw0rd123")


def test_password_policy_and_hash():
    assert auth.password_problem("short1A") and auth.password_problem("alllowercase123") is not None
    assert auth.password_problem(PW) is None
    h = auth.hash_password(PW)
    assert auth.verify_password(PW, h) and not auth.verify_password("x", h) and h != auth.hash_password(PW)
