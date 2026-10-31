"""Read documents: Tesseract for images, a line parser for typed text.

Returns structured fields with a confidence. An unreadable document is reported as unreadable,
never guessed.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from dateutil import parser as dateparser

from relief.contracts.schemas import DocFields, DocRef

log = logging.getLogger(__name__)

LABELS: dict[str, list[str]] = {
    "name": ["name", "patient name", "beneficiary name", "name of beneficiary", "name of patient"],
    "card_id": [
        "card id", "card no", "card number", "pmjay id", "pm-jay id", "ab pm-jay id", "ayushman id",
        "health id", "beneficiary id", "arogya id", "ark id", "ark no", "aarogyasri id", "aarogyasri no",
        "mjpjay id", "cmchis id", "cmchis urn", "swasthya sathi id", "jan aadhaar", "aadhaar", "aadhaar no",
        "uidai", "abha", "abha id", "abha no",
    ],
    "family_id": ["family id", "ration card", "ration card no", "family card", "rc no", "bpl card", "ration card number", "aay card", "phh card"],
    "dob": ["dob", "date of birth", "d.o.b"],
    "hospital": ["hospital", "hospital name", "name of hospital"],
    "procedure": ["procedure", "procedure code", "package", "package code"],
    "referral_id": ["referral id", "referral no", "referral letter no", "referral number"],
    "referral_date": ["referral date", "date of referral", "referred on"],
    "state": ["state"],
}
_LABEL_TO_KEY = {lab: key for key, labs in LABELS.items() for lab in labs}
_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z .\-/]{1,40}?)\s*[:=\-]\s*(.+?)\s*$")

MIN_CONF_OK = 60.0
MIN_CONF_PARTIAL = 30.0


_ISO = re.compile(r"^\s*(\d{4})-(\d{1,2})-(\d{1,2})\s*$")


def normalise_dob(value: str) -> Optional[str]:
    """Indian documents write day first (02/01/1990 = 2 January). ISO dates are read as year-month-day."""
    try:
        m = _ISO.match(value)
        if m:
            d = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        else:
            d = dateparser.parse(value, dayfirst=True, fuzzy=False)
    except (ValueError, OverflowError, TypeError):
        return None
    if d is None:
        return None
    dd: date = d.date()
    if dd.year < 1900 or dd > date.today():
        return None
    return dd.isoformat()


def parse_text_fields(text: str) -> dict[str, str]:
    """Extract 'Label: value' pairs for known labels. First occurrence wins."""
    out: dict[str, str] = {}
    for raw in text.splitlines():
        m = _LINE.match(raw)
        if not m:
            continue
        label = re.sub(r"\s+", " ", m.group(1).strip().lower())
        key = _LABEL_TO_KEY.get(label)
        if key is None or key in out:
            continue
        value = m.group(2).strip()
        if key in ("dob", "referral_date"):
            iso = normalise_dob(value) if key == "dob" else _iso_date(value)
            if iso is None:
                continue
            value = iso
        out[key] = value
    return out


def _iso_date(value: str) -> Optional[str]:
    try:
        return dateparser.parse(value, dayfirst=True).date().isoformat()
    except (ValueError, OverflowError, TypeError):
        return None


def _ocr_image(path: Path) -> tuple[str, float, str]:
    """Return (text, mean word confidence 0-100, note)."""
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:  # pragma: no cover
        return "", 0.0, f"OCR libraries missing: {exc}"
    try:
        img = Image.open(path)
        img = ImageOps.exif_transpose(img).convert("L")
        if min(img.size) < 900:
            scale = 900 / min(img.size)
            img = img.resize((int(img.width * scale), int(img.height * scale)))
        img = ImageOps.autocontrast(img)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT, config="--psm 6")
    except pytesseract.TesseractNotFoundError:
        return "", 0.0, "The Tesseract OCR program is not installed."
    except (OSError, ValueError) as exc:
        return "", 0.0, f"Image could not be opened: {exc}"
    words, confs = [], []
    lines: dict[tuple, list[str]] = {}
    for i, w in enumerate(data["text"]):
        if not w.strip():
            continue
        c = float(data["conf"][i])
        if c < 0:
            continue
        words.append(w)
        confs.append(c)
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(w)
    text = "\n".join(" ".join(ws) for ws in lines.values())
    mean = sum(confs) / len(confs) if confs else 0.0
    return text, mean, ""


def read_document(doc: DocRef) -> DocFields:
    note = ""
    if doc.text:
        text, conf = doc.text, 100.0
    elif doc.path:
        p = Path(doc.path)
        if not p.is_file():
            return DocFields(doc_id=doc.doc_id, kind=doc.kind, status="unreadable", note="File not found.")
        text, conf, note = _ocr_image(p)
    else:  # pragma: no cover - validated by DocRef
        return DocFields(doc_id=doc.doc_id, kind=doc.kind, status="unreadable", note="No source.")
    fields = parse_text_fields(text) if text.strip() else {}
    if not fields or conf < MIN_CONF_PARTIAL:
        return DocFields(doc_id=doc.doc_id, kind=doc.kind, fields=fields if conf >= MIN_CONF_PARTIAL else {},
                         confidence=round(conf / 100, 3), status="unreadable",
                         note=note or "No recognised fields could be read with enough confidence.")
    status = "ok" if conf >= MIN_CONF_OK and len(fields) >= 2 else "partial"
    return DocFields(doc_id=doc.doc_id, kind=doc.kind, fields=fields, confidence=round(conf / 100, 3), status=status, note=note)


def read_documents(docs: list[DocRef]) -> list[DocFields]:
    return [read_document(d) for d in docs]
