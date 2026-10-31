"""Compare the card data with fields read from documents. Pure code; lists every difference."""
from __future__ import annotations

import re

from rapidfuzz import fuzz

from relief.contracts.schemas import CardData, DocFields, Mismatch, RecordCheck
from relief.tools.ocr import normalise_dob

HONORIFICS = re.compile(r"\b(mr|mrs|ms|miss|smt|shri|sri|dr|late)\b\.?", re.I)
EXACT_MATCH = 100.0
VARIANT_FLOOR = 80.0


def norm_name(s: str) -> str:
    s = HONORIFICS.sub(" ", s.lower())
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_id(s: str) -> str:
    return re.sub(r"[\s\-/]", "", s).upper()


def check_records(card: CardData, docs: list[DocFields]) -> RecordCheck:
    mismatches: list[Mismatch] = []
    compared = 0
    seen_fields: set[str] = set()
    card_values = {
        "name": card.name,
        "card_id": card.card_id,
        "family_id": card.family_id,
        "dob": card.dob.isoformat() if card.dob else None,
    }
    for d in docs:
        if d.status == "unreadable":
            continue
        for field, cval in card_values.items():
            dval = d.fields.get(field)
            if cval is None or dval is None:
                continue
            seen_fields.add(field)
            compared += 1
            if field == "name":
                a, b = norm_name(cval), norm_name(dval)
                score = fuzz.token_sort_ratio(a, b)
                if score >= EXACT_MATCH:
                    continue
                kind = "possible_variant" if score >= VARIANT_FLOOR else "different"
                mismatches.append(Mismatch(field=field, card_value=cval, doc_value=dval, doc_id=d.doc_id,
                                           kind=kind, similarity=round(score, 1)))
            elif field in ("card_id", "family_id"):
                if norm_id(cval) != norm_id(dval):
                    mismatches.append(Mismatch(field=field, card_value=cval, doc_value=dval, doc_id=d.doc_id, kind="different"))
            elif field == "dob":
                dn = normalise_dob(dval) or dval
                if dn != cval:
                    mismatches.append(Mismatch(field=field, card_value=cval, doc_value=dval, doc_id=d.doc_id, kind="different"))
    unknown = [f for f, v in card_values.items() if v is not None and f not in seen_fields]
    unreadable = [d.doc_id for d in docs if d.status == "unreadable"]
    unknown += [f"document {i} could not be read" for i in unreadable]
    if mismatches:
        status = "mismatch"
    elif compared > 0:
        status = "consistent"
    else:
        status = "unknown"
    return RecordCheck(mismatches=mismatches, unknown=unknown, compared_fields=compared, status=status)  # type: ignore[arg-type]
