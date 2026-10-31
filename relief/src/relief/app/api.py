"""FastAPI service for the web app. Everything is under /api; the built frontend (if present) is served at /.

Run:  python -m uvicorn relief.app.api:create_app --factory --port 8000
"""
from __future__ import annotations

import platform
import re
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

from fastapi import BackgroundTasks, Depends, FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from relief import __version__
from relief.agent.service import Agent, CaseExists, NoSuchCase, NotAwaitingApproval
from relief.app import auth, scheduler
from relief.app.db import Database
from relief.app.executor import AppExecutor
from relief.config import Settings, get_settings
from relief.contracts.schemas import CaseInput, CaseResult, CaseStatus, Decision
from relief.llm.client import LLM, OllamaClient
from relief.tools import Registry

ALLOWED_SUFFIX = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}
MAGIC = (b"\x89PNG", b"\xff\xd8\xff", b"II*\x00", b"MM\x00*", b"BM")
CASE_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")
_DUMMY_HASH = auth.hash_password("not-a-real-password-Ab1")


class LoginIn(BaseModel):
    email: str = Field(max_length=200)
    password: str = Field(max_length=200)


class PasswordIn(BaseModel):
    current: str = Field(max_length=200)
    new: str = Field(max_length=200)


class UserIn(BaseModel):
    email: str = Field(max_length=200)
    name: str = Field(min_length=1, max_length=100)
    role: Literal["admin", "facilitator"] = "facilitator"
    password: str = Field(max_length=200)


class UserPatch(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    role: Optional[Literal["admin", "facilitator"]] = None
    active: Optional[bool] = None
    new_password: Optional[str] = Field(default=None, max_length=200)


def public_user(u: dict) -> dict:
    return {"id": u["id"], "email": u["email"], "name": u["name"], "role": u["role"], "active": bool(u["active"]),
            "created_at": u.get("created_at"), "last_login": u.get("last_login")}


def create_app(settings: Optional[Settings] = None, llm: Optional[LLM] = "auto", start_scheduler: bool = True) -> FastAPI:  # type: ignore[assignment]
    settings = settings or get_settings()
    settings.var_dir.mkdir(parents=True, exist_ok=True)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    db = Database(settings.db_path)
    secret = auth.load_secret(settings)
    model = OllamaClient(settings) if llm == "auto" else llm
    agent = Agent(settings, llm=model, executor=AppExecutor(db))
    registry: Registry = agent.registry
    throttle = auth.Throttle()
    sched: dict = {"s": None}

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if start_scheduler:
            sched["s"] = scheduler.start(db)
        yield
        if sched["s"]:
            sched["s"].shutdown(wait=False)

    app = FastAPI(title="RELIEF", version=__version__, lifespan=lifespan, docs_url="/api/docs", openapi_url="/api/openapi.json",
                  description="Finds why cashless treatment is blocked and prepares a fix for a person to approve. "
                              "Not medical advice; makes no eligibility decisions.")
    app.add_middleware(CORSMiddleware, allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
                       allow_methods=["*"], allow_headers=["*"])
    bearer = HTTPBearer(auto_error=False)

    # ------------------------------------------------------------------ auth helpers
    def current_user(cred: Optional[HTTPAuthorizationCredentials] = Depends(bearer)) -> dict:
        uid = auth.read_token(secret, cred.credentials) if cred else None
        user = db.get_user_id(uid) if uid else None
        if not user or not user["active"]:
            raise HTTPException(401, "Please sign in again.")
        return user

    def admin_only(user: dict = Depends(current_user)) -> dict:
        if user["role"] != "admin":
            raise HTTPException(403, "Administrators only.")
        return user

    def check_id(case_id: str) -> None:
        if not CASE_ID.fullmatch(case_id):
            raise HTTPException(422, "Invalid case id")

    def case_access(case_id: str, user: dict) -> dict:
        check_id(case_id)
        row = db.get_case_row(case_id)
        if not row or (user["role"] != "admin" and row["created_by"] != user["email"]):
            raise HTTPException(404, "No such case")
        return row

    def result_for(row: dict) -> dict:
        try:
            res = agent.get_result(row["case_id"])
        except (NoSuchCase, KeyError):
            status = CaseStatus.ERROR if row["status"] == "error" else CaseStatus.RUNNING
            case = CaseInput.model_validate_json(row["case_json"])
            res = CaseResult(case_id=row["case_id"], status=status, synthetic=case.synthetic, error=row.get("error"))
        except Exception as exc:
            log.warning("get_result fallback for %s: %s", row["case_id"], exc)
            status = CaseStatus.ERROR if row["status"] == "error" else CaseStatus.RUNNING
            case = CaseInput.model_validate_json(row["case_json"])
            res = CaseResult(case_id=row["case_id"], status=status, synthetic=case.synthetic, error=str(exc))
        if row["status"] == "error" and res.status == CaseStatus.RUNNING:
            res.status, res.error = CaseStatus.ERROR, row.get("error")
        out = res.model_dump(mode="json")
        case = CaseInput.model_validate_json(row["case_json"])
        out["meta"] = {"created_by": row["created_by"], "created_at": row["created_at"], "case": case.model_dump(mode="json")}
        return out

    # ------------------------------------------------------------------ public
    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "registry_synthetic": registry.synthetic}

    @app.post("/api/auth/login")
    def login(body: LoginIn, request: Request) -> dict:
        email = body.email.strip().lower()
        key = f"{email}|{request.client.host if request.client else '-'}"
        if throttle.blocked(key):
            raise HTTPException(429, "Too many attempts. Wait 15 minutes and try again.")
        user = db.get_user(email)
        ok = auth.verify_password(body.password, user["password_hash"] if user else _DUMMY_HASH)
        if not (user and ok and user["active"]):
            throttle.fail(key)
            db.audit(email or "-", "login.failed")
            raise HTTPException(401, "Email or password is not correct.")
        throttle.clear(key)
        db.update_user(user["id"], last_login=datetime.now(timezone.utc).isoformat())
        db.audit(user["email"], "login")
        return {"token": auth.make_token(secret, user, settings.token_hours), "user": public_user(user)}

    @app.post("/api/auth/register", status_code=201)
    def register(body: UserIn) -> dict:
        email = body.email.strip().lower()
        if not auth.valid_email(email):
            raise HTTPException(422, "That does not look like a valid email address.")
        if db.get_user(email):
            raise HTTPException(409, "An account with that email already exists.")
        if (p := auth.password_problem(body.password)):
            raise HTTPException(422, p)
        uid = db.add_user(email, body.name.strip(), body.role, auth.hash_password(body.password))
        user = db.get_user_id(uid)
        db.audit(email, "user.register", detail=f"{body.name.strip()} ({body.role})")
        return {"token": auth.make_token(secret, user, settings.token_hours), "user": public_user(user)}

    # ------------------------------------------------------------------ account
    @app.get("/api/auth/me")
    def me(user: dict = Depends(current_user)) -> dict:
        return public_user(user)

    @app.post("/api/auth/password")
    def change_password(body: PasswordIn, user: dict = Depends(current_user)) -> dict:
        if not auth.verify_password(body.current, user["password_hash"]):
            raise HTTPException(400, "Current password is not correct.")
        if (p := auth.password_problem(body.new)):
            raise HTTPException(422, p)
        db.update_user(user["id"], password_hash=auth.hash_password(body.new))
        db.audit(user["email"], "password.change")
        return {"ok": True}

    # ------------------------------------------------------------------ reference data
    @app.get("/api/registry/hospitals")
    def hospitals(_: dict = Depends(current_user)) -> list[dict]:
        return [{"hospital_id": h.hospital_id, "name": h.name, "type": h.type, "district": h.district, "state": h.state,
                 "specialties": h.specialties, "empanelment_active": h.empanelment_active} for h in registry.hospitals()]

    @app.get("/api/registry/packages")
    def packages(_: dict = Depends(current_user)) -> list[dict]:
        return [{"code": p.code, "name": p.name, "specialty": p.specialty, "tier": p.tier,
                 "reserved_for_public": p.reserved_for_public, "required_docs": p.required_docs} for p in registry.packages()]

    @app.get("/api/registry/info")
    def registry_info(_: dict = Depends(current_user)) -> dict:
        return {"version": registry.version, "synthetic": registry.synthetic, "note": registry.data.note}

    # ------------------------------------------------------------------ uploads
    @app.post("/api/uploads")
    async def upload(file: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in ALLOWED_SUFFIX:
            raise HTTPException(415, f"Only image files are accepted ({', '.join(sorted(ALLOWED_SUFFIX))}).")
        data = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
        if len(data) > settings.max_upload_mb * 1024 * 1024:
            raise HTTPException(413, f"File larger than {settings.max_upload_mb} MB.")
        if not data.startswith(MAGIC):
            raise HTTPException(415, "The file content is not a supported image.")
        name = f"{uuid.uuid4().hex}{suffix}"
        (settings.upload_dir / name).write_bytes(data)
        return {"path": str(settings.upload_dir / name), "bytes": len(data), "name": file.filename}

    # ------------------------------------------------------------------ cases
    def run_job(case: CaseInput) -> None:
        try:
            res = agent.run_case(case)
            db.update_case(case.case_id, res.status.value, res.main_blocker.value if res.main_blocker else None)
            db.audit("system", "case.analysed", case.case_id, f"{res.status.value}; blocker={res.main_blocker.value if res.main_blocker else '-'}")
        except Exception as exc:  # shown to the person; never crash the worker thread silently
            db.update_case(case.case_id, "error", None, f"{type(exc).__name__}: {exc}"[:500])
            db.audit("system", "case.error", case.case_id, str(exc))

    @app.post("/api/cases", status_code=202)
    def create_case(case: CaseInput, tasks: BackgroundTasks, user: dict = Depends(current_user)) -> dict:
        for d in case.documents:
            if d.path:
                p = Path(d.path).resolve()
                if settings.upload_dir.resolve() not in p.parents or not p.is_file():
                    raise HTTPException(422, f"Document {d.doc_id}: the file was not uploaded through the app.")
        if registry.hospital(case.hospital_id) is None:
            raise HTTPException(422, f"Unknown hospital {case.hospital_id}")
        if registry.package(case.procedure_code) is None:
            raise HTTPException(422, f"Unknown procedure {case.procedure_code}")
        if db.case_exists(case.case_id):
            raise HTTPException(409, f"Case {case.case_id} already exists")
        db.save_case(case.case_id, "running", None, case.synthetic, case.model_dump_json(), user["email"])
        db.audit(user["email"], "case.create", case.case_id)
        tasks.add_task(run_job, case)
        return {"case_id": case.case_id, "status": "running"}

    @app.get("/api/cases")
    def cases(limit: int = Query(100, ge=1, le=500), status: Optional[str] = None, blocker: Optional[str] = None,
              q: Optional[str] = Query(None, max_length=64), user: dict = Depends(current_user)) -> list[dict]:
        return db.list_cases(limit, None if user["role"] == "admin" else user["email"], status, blocker, q)

    @app.get("/api/cases/{case_id}")
    def get_case(case_id: str, user: dict = Depends(current_user)) -> dict:
        return result_for(case_access(case_id, user))

    @app.post("/api/cases/{case_id}/decision")
    def decide(case_id: str, decision: Decision, user: dict = Depends(current_user)) -> dict:
        row = case_access(case_id, user)
        decision = decision.model_copy(update={"decided_by": f"{user['name']} <{user['email']}>"})
        try:
            res = agent.resume_case(case_id, decision)
        except NoSuchCase:
            raise HTTPException(404, "No such case")
        except NotAwaitingApproval:
            raise HTTPException(409, "This case is not waiting for a decision.")
        db.add_decision(case_id, decision.action, decision.decided_by, decision.note)
        db.update_case(case_id, res.status.value, res.main_blocker.value if res.main_blocker else None)
        db.audit(user["email"], f"case.{decision.action}", case_id, decision.note)
        return result_for(db.get_case_row(case_id) or row)

    @app.get("/api/cases/{case_id}/log")
    def case_log(case_id: str, user: dict = Depends(current_user)) -> dict:
        case_access(case_id, user)
        return {"decisions": db.decisions(case_id), "submissions": db.submissions(case_id), "audit": db.audit_log(100, case_id)}

    # ------------------------------------------------------------------ dashboard + reminders
    @app.get("/api/stats")
    def stats(user: dict = Depends(current_user)) -> dict:
        s = db.stats(None if user["role"] == "admin" else user["email"])
        s["reminders_due"] = len([r for r in db.reminders("due") if db.get_case_row(r["case_id"]) and (user["role"] == "admin" or db.get_case_row(r["case_id"])["created_by"] == user["email"])])
        return s

    def mine(user: dict, rems: list[dict]) -> list[dict]:
        if user["role"] == "admin":
            return rems
        ok = {c["case_id"] for c in db.list_cases(500, user["email"])}
        return [r for r in rems if r["case_id"] in ok]

    @app.get("/api/reminders")
    def reminders(state: Optional[str] = None, user: dict = Depends(current_user)) -> list[dict]:
        db.fire_due_reminders()
        return mine(user, db.reminders(state))

    @app.post("/api/reminders/{rid}/done")
    def reminder_done(rid: int, user: dict = Depends(current_user)) -> dict:
        if rid not in {r["id"] for r in mine(user, db.reminders())}:
            raise HTTPException(404, "No such reminder")
        db.dismiss_reminder(rid)
        return {"ok": True}

    # ------------------------------------------------------------------ admin
    @app.get("/api/admin/users")
    def list_users(_: dict = Depends(admin_only)) -> list[dict]:
        return [public_user(u) for u in db.users()]

    @app.post("/api/admin/users", status_code=201)
    def add_user(body: UserIn, admin: dict = Depends(admin_only)) -> dict:
        if not auth.valid_email(body.email):
            raise HTTPException(422, "That does not look like an email address.")
        if db.get_user(body.email):
            raise HTTPException(409, "A user with that email already exists.")
        if (p := auth.password_problem(body.password)):
            raise HTTPException(422, p)
        uid = db.add_user(body.email, body.name.strip(), body.role, auth.hash_password(body.password))
        db.audit(admin["email"], "user.create", detail=f"{body.email} ({body.role})")
        return public_user(db.get_user_id(uid))  # type: ignore[arg-type]

    @app.patch("/api/admin/users/{uid}")
    def patch_user(uid: int, body: UserPatch, admin: dict = Depends(admin_only)) -> dict:
        u = db.get_user_id(uid)
        if not u:
            raise HTTPException(404, "No such user")
        fields: dict = {}
        if body.name is not None:
            fields["name"] = body.name.strip()
        if body.role is not None:
            fields["role"] = body.role
        if body.active is not None:
            fields["active"] = int(body.active)
        losing_admin = u["role"] == "admin" and u["active"] and (fields.get("role") == "facilitator" or fields.get("active") == 0)
        if losing_admin and db.count_active_admins() <= 1:
            raise HTTPException(409, "There must be at least one active administrator.")
        if uid == admin["id"] and fields.get("active") == 0:
            raise HTTPException(409, "You cannot disable your own account.")
        if body.new_password:
            if (p := auth.password_problem(body.new_password)):
                raise HTTPException(422, p)
            fields["password_hash"] = auth.hash_password(body.new_password)
        db.update_user(uid, **fields)
        db.audit(admin["email"], "user.update", detail=f"{u['email']}: {', '.join(k for k in fields if k != 'password_hash')}{' +password' if 'password_hash' in fields else ''}")
        return public_user(db.get_user_id(uid))  # type: ignore[arg-type]

    @app.get("/api/admin/rules")
    def admin_rules(_: dict = Depends(admin_only)) -> list[dict]:
        return [r.model_dump(mode="json") for r in agent.kb.all()]

    @app.get("/api/admin/audit")
    def admin_audit(limit: int = Query(200, ge=1, le=1000), _: dict = Depends(admin_only)) -> list[dict]:
        return db.audit_log(limit)

    @app.get("/api/admin/system")
    def system(_: dict = Depends(admin_only)) -> dict:
        ok, msg = model.health() if model is not None else (False, "No model configured; rule-based fallbacks are used")
        emb_ok, emb_msg = True, f"{settings.embedder}"
        try:
            agent.kb.search("referral", k=1)
            emb_msg = f"{agent.kb.embedder.name} ready"
        except Exception as exc:
            emb_ok, emb_msg = False, str(exc)[:300]
        return {"version": __version__, "python": platform.python_version(), "model": settings.llm_model, "model_ok": ok,
                "model_message": msg, "embedder": settings.embedder, "embedder_ok": emb_ok, "embedder_message": emb_msg,
                "rules": len(agent.kb.ids()), "rules_checked": sum(1 for r in agent.kb.all() if r.quote_checked),
                "registry_version": registry.version, "registry_synthetic": registry.synthetic,
                "hospitals": len(registry.hospitals()), "packages": len(registry.packages()), "users": db.count_users()}

    app.state.agent, app.state.db = agent, db

    # ------------------------------------------------------------------ frontend (built files), if present
    dist = settings.frontend_dist
    if (dist / "index.html").is_file():
        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            if path.startswith("api/"):
                raise HTTPException(404, "Not found")
            f = (dist / path).resolve()
            if path and dist.resolve() in f.parents and f.is_file():
                return FileResponse(f)
            return FileResponse(dist / "index.html")

    return app
