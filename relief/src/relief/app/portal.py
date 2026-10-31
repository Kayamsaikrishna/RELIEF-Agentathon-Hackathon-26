"""Pre-authorisation SIMULATOR.

This is not the Transaction Management System of PM-JAY and is not connected to any government system. It accepts a
submission, checks that the payload is complete and returns a reference number so the full flow can be run and tested.
Every response is labelled as simulated. Replace `submit` with a real integration only with the programme's approval.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from relief.contracts.schemas import CaseInput

LABEL = "SIMULATED: not sent to any government system"


def submit(case: CaseInput, payload: dict) -> dict:
    missing = [k for k in ("hospital_id", "procedure_code", "card_id") if not (payload.get(k) or getattr(case, k, None) or
                                                                              (case.card.card_id if k == "card_id" else None))]
    if missing:
        return {"accepted": False, "label": LABEL, "errors": [f"missing {m}" for m in missing]}
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    ref = "SIM-" + hashlib.sha1(f"{case.case_id}{stamp}".encode()).hexdigest()[:10].upper()
    return {"accepted": True, "reference": ref, "label": LABEL, "received_at": stamp}
