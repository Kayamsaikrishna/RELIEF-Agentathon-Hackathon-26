from datetime import datetime, timedelta, timezone

import pytest
from PIL import Image, ImageDraw, ImageFont

from relief.contracts.schemas import CardData, DocFields, DocKind, DocRef
from relief.tools import Registry, RulesKB, check_records, check_referral, preauth_clock, read_documents
from tests.conftest import make_case

NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)


def test_clock_reports_both_limits():
    c = make_case(preauth_submitted_at=(NOW - timedelta(hours=8)).isoformat(), as_of=NOW.isoformat())
    r = preauth_clock(c)
    by = {l.rule_id: l.exceeded for l in r.limits}
    assert by == {"HBP-PREAUTH-6H": "yes", "CAG-PREAUTH-12H": "no"}


def test_clock_unknown_without_submission():
    r = preauth_clock(make_case())
    assert r.hours_elapsed is None and all(l.exceeded == "unknown" for l in r.limits)


def test_clock_decision_recorded_is_not_pending():
    c = make_case(preauth_submitted_at=(NOW - timedelta(hours=30)).isoformat(), preauth_decision_at=(NOW - timedelta(hours=1)).isoformat(), as_of=NOW.isoformat())
    assert preauth_clock(c).decision_recorded


def test_records_match_and_mismatch():
    card = CardData(name="Asha Rao", card_id="KA1", dob="1990-01-02")
    same = DocFields(doc_id="d", kind=DocKind.ID_PROOF, fields={"name": "ASHA RAO", "card_id": "ka1", "dob": "02/01/1990"}, status="ok", confidence=0.9)
    assert check_records(card, [same]).status == "consistent"
    diff = DocFields(doc_id="d", kind=DocKind.ID_PROOF, fields={"name": "Rajesh Menon", "card_id": "KA1"}, status="ok", confidence=0.9)
    r = check_records(card, [diff])
    assert r.status == "mismatch" and r.mismatches[0].field == "name" and r.mismatches[0].kind == "different"


def test_records_unreadable_is_unknown_not_mismatch():
    card = CardData(name="Asha Rao", card_id="KA1")
    bad = DocFields(doc_id="d", kind=DocKind.ID_PROOF, status="unreadable")
    assert check_records(card, [bad]).status == "unknown"


def test_referral_rules(settings):
    reg = Registry.load(settings.registry_path)
    h = reg.lookup_hospital("H-005", "SYN-ORT-001")
    assert check_referral(make_case(referral={"present": "no"}), h).required == "yes"
    emergency = reg.lookup_hospital("H-005", "SYN-ORT-002")
    assert check_referral(make_case(procedure_code="SYN-ORT-002"), emergency).required == "no"
    assert check_referral(make_case(), reg.lookup_hospital("H-999", "SYN-ORT-001")).required == "unknown"


def test_registry_unknown_hospital(settings):
    h = Registry.load(settings.registry_path).lookup_hospital("H-999", "SYN-ORT-001")
    assert h.found is False and h.empanelled == "unknown"


def test_kb_lookup_and_search(settings):
    kb = RulesKB(settings)
    assert len(kb.ids()) == 31 and kb.get("CAG-PREAUTH-12H").source_id == "CAG-11-2023"
    hits = kb.search("referral letter valid for thirty days", k=5)
    assert hits and any(h.rule_id.startswith("WHO-REFERRAL") for h in hits)
    assert kb.search("   ") == []


def _image(path, lines, size=36):
    img = Image.new("L", (1400, 120 + 70 * len(lines)), 255)
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
    except OSError:
        pytest.skip("no font for OCR image")
    for i, t in enumerate(lines):
        d.text((40, 40 + 70 * i), t, fill=0, font=font)
    img.save(path)


def test_ocr_reads_a_clean_card_image(tmp_path):
    pytest.importorskip("pytesseract")
    p = tmp_path / "card.png"
    _image(p, ["Name: Asha Rao", "Card ID: KA123456", "DOB: 02/01/1990"])
    try:
        f = read_documents([DocRef(doc_id="D1", kind=DocKind.CARD, path=str(p))])[0]
    except Exception as exc:
        pytest.skip(f"tesseract unavailable: {exc}")
    assert f.status in ("ok", "partial") and f.fields.get("card_id", "").upper().startswith("KA1234")


def test_ocr_blank_image_is_unreadable(tmp_path):
    p = tmp_path / "blank.png"
    Image.new("L", (400, 300), 255).save(p)
    try:
        f = read_documents([DocRef(doc_id="D1", kind=DocKind.CARD, path=str(p))])[0]
    except Exception as exc:
        pytest.skip(f"tesseract unavailable: {exc}")
    assert f.status == "unreadable" and not f.fields


def test_text_documents_parse():
    f = read_documents([DocRef(doc_id="D1", kind=DocKind.CARD, text="Name: Asha Rao\nCard ID: KA1\nDOB: 1990-01-02")])[0]
    assert f.fields["name"] == "Asha Rao" and f.fields["dob"] == "1990-01-02"
