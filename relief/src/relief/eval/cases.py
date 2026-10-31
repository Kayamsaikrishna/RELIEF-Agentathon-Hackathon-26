"""The 30 synthetic evaluation cases and their answer keys.

Each case is built by changing exactly one thing in a clean file, so the intended blocker is known by construction
(from the rule passages cited in `why`), not by running the agent. All people, ids and hospitals are invented.
NOTE: the agent's rule-based path implements the same rules, so a high score here shows the code is consistent with
the rules; it is not evidence about real-world accuracy. See docs/EVALUATION.md.
"""
from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from typing import Any

DEV = {0, 5, 8, 10, 14, 16, 19, 22, 25, 28}  # spread over blockers and reason styles
AS_OF = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
ADMIT = date(2026, 10, 18)
NAMES = ["Asha Rao", "Mohan Gowda", "Lakshmi Devi", "Ravi Kumar", "Sunita Patil", "Imran Shaikh", "Kavya Nair", "Basavaraj Hiremath"]


def _doc_texts(card: dict, hospital: str, proc: str, referral_date: date | None) -> dict[str, str]:
    ident = f"Name: {card['name']}\nCard ID: {card['card_id']}\nDOB: {card['dob']}"
    d = {"card": ident, "id_proof": ident, "preauth_form": f"Hospital: {hospital}\nProcedure: {proc}",
         "clinical_notes": f"Hospital: {hospital}\nProcedure: {proc}", "diagnostic_report": f"Hospital: {hospital}"}
    if referral_date:
        d["referral_letter"] = f"Referral ID: REF-{card['card_id'][-3:]}\nReferral Date: {referral_date.isoformat()}"
    return d


def _base(i: int, hospital: str = "H-005", proc: str = "SYN-ORT-001", referral: bool = True) -> dict[str, Any]:
    card = {"name": NAMES[i % len(NAMES)], "card_id": f"KA{700100 + i}", "dob": f"19{60 + i % 30}-0{1 + i % 9}-1{i % 9}"}
    ref_date = ADMIT - timedelta(days=10) if referral else None
    texts = _doc_texts(card, hospital, proc, ref_date)
    return {"case_id": f"EV-{i:02d}", "card": {**card}, "hospital_id": hospital, "procedure_code": proc, "synthetic": True,
            "refusal_reason": "Pre-authorisation cannot be taken now, come back later.", "admission_date": ADMIT.isoformat(),
            "as_of": AS_OF.isoformat(),
            "referral": {"present": "yes", "issued_on": ref_date.isoformat()} if referral else {"present": "no"},
            "documents": [{"doc_id": f"D{n+1}", "kind": k, "text": t} for n, (k, t) in enumerate(texts.items())]}


def _drop(c: dict, kind: str) -> dict:
    c["documents"] = [d for d in c["documents"] if d["kind"] != kind]
    return c


def build() -> list[dict]:
    out: list[dict] = []

    def add(expected: str, why: str, case: dict, reason: str | None = None) -> None:
        if reason:
            case["refusal_reason"] = reason
        case["case_id"] = f"EV-{len(out):02d}"
        out.append({"case": case, "expected_blocker": expected, "why": why})

    n = lambda: len(out)  # noqa: E731
    # REFERRAL (rules WHO-2B3A-REFERRAL, WHO-REFERRAL-VALID-30D, WHO-RETROSPECTIVE-REFERRAL)
    c = _base(n(), referral=False); c["referral"] = {"present": "no"}
    add("REFERRAL", "Tier 3A at a private hospital with no referral (WHO-2B3A-REFERRAL).", c, "Your file is not complete, we cannot admit under the scheme.")
    c = _base(n()); c["referral"]["issued_on"] = (ADMIT - timedelta(days=55)).isoformat()
    add("REFERRAL", "Referral 55 days old; valid 30 days (WHO-REFERRAL-VALID-30D).", c, "Referral is not accepted.")
    c = _base(n()); c["referral"]["issued_on"] = (ADMIT + timedelta(days=2)).isoformat()
    add("REFERRAL", "Referral issued after admission (WHO-RETROSPECTIVE-REFERRAL).", c, "System is not accepting this case.")
    c = _base(n(), hospital="H-012", referral=False); c["referral"] = {"present": "no"}
    add("REFERRAL", "Tier 3A at a private hospital with no referral.", c, "Take the patient to the district hospital first.")
    # ENTITLEMENT
    for reason in ["Your card is not valid.", "No record of you in our system.", "You are not eligible for this scheme.", "Card is not showing in the portal."]:
        c = _base(n()); c["bis_status"] = "not_found"
        add("ENTITLEMENT", "Beneficiary lookup entered by a person returned no match (PMJAY-FLOW-ELIGIBILITY).", c, reason)
    # LINKAGE
    c = _base(n()); [d.update(text=d["text"].replace(c["card"]["name"], "Rajesh Menon")) for d in c["documents"] if d["kind"] == "id_proof"]
    add("LINKAGE", "Name on the id proof differs entirely from the card (OPS-BIS-DOCUMENTS).", c, "Documents do not match, system rejected.")
    c = _base(n()); [d.update(text=d["text"].replace("DOB: " + c["card"]["dob"], "DOB: 1951-12-30")) for d in c["documents"] if d["kind"] == "id_proof"]
    add("LINKAGE", "Date of birth on the id proof differs from the card.", c, "Verification failed.")
    c = _base(n()); [d.update(text=d["text"].replace(c["card"]["card_id"], "KA999999")) for d in c["documents"] if d["kind"] == "id_proof"]
    add("LINKAGE", "Card id on the id proof differs from the card.", c, "Card number problem.")
    c = _base(n()); [d.update(text=d["text"].replace(c["card"]["name"], c["card"]["name"].replace("Rao", "Raoo").replace("Kumar", "Kumaar").replace("Gowda", "Gouda").replace("Devi", "Devy").replace("Patil", "Patel").replace("Shaikh", "Sheikh").replace("Nair", "Nayar").replace("Hiremath", "Hiremat"))) for d in c["documents"] if d["kind"] == "id_proof"]
    add("LINKAGE", "Spelling variant of the name on the id proof (possible variant).", c, "Name mismatch in our system.")
    # IMPROPER_CHARGE (HBP-CASHLESS, HBP-ADVANCE-DISCLOSURE, OPS-NO-CHARGE)
    for amt, purpose, reason in [(5000, "deposit", "Pay a deposit first."), (1800, "medicines from outside", "Buy the medicines yourself."),
                                 (12000, "implant cost", "Scheme does not cover this, pay the difference."), (3000, "admission fee", "Pay before admission.")]:
        c = _base(n()); c["payment_request"] = {"amount_inr": amt, "purpose": purpose, "wallet_exhausted": "no", "disclosed_in_advance": "no"}
        add("IMPROPER_CHARGE", "Payment requested although cashless, wallet not exhausted, nothing disclosed in advance.", c, reason)
    # EMPANELMENT
    c = _base(n(), hospital="H-011")
    add("EMPANELMENT", "Hospital empanelment not active in the registry (HBP-SPECIALTY-EMPANELMENT).", c, "We are not part of the scheme for this.")
    c = _base(n(), hospital="H-002")
    add("EMPANELMENT", "Hospital does not list orthopaedics (HBP-SPECIALTY-EMPANELMENT).", c, "This procedure is not done here under the scheme.")
    c = _base(n(), hospital="H-006", proc="SYN-OPH-001", referral=False); c["referral"] = {"present": "unknown"}
    add("EMPANELMENT", "Tier 2A procedure at a private hospital (WHO-2A-GOVERNMENT).", c, "Package blocked.")
    c = _base(n(), hospital="H-004")
    add("EMPANELMENT", "Cardiology-only hospital for an orthopaedic package.", c, "Package not available.")
    # FORMS (HBP-DOCS-VARY)
    for kind in ["diagnostic_report", "clinical_notes", "preauth_form", "id_proof"]:
        add("FORMS", f"Required document missing: {kind}.", _drop(_base(n()), kind), "Pre-authorisation was rejected.")
    # ESCALATION_ONLY (CAG-PREAUTH-12H, HBP-PREAUTH-6H)
    for hrs in (30, 14, 50):
        c = _base(n()); c["preauth_submitted_at"] = (AS_OF - timedelta(hours=hrs)).isoformat()
        add("ESCALATION_ONLY", f"All checks consistent; pre-authorisation pending {hrs} hours with no decision.", c, "Still waiting for approval from the insurer.")
    # INSUFFICIENT_EVIDENCE: hospital not in the registry, nothing else to go on
    for k in range(3):
        c = _base(n(), hospital=f"H-90{k}"); c["documents"] = []
        add("INSUFFICIENT_EVIDENCE", "Hospital not in the registry and no documents, so no check can be completed.", c, "They said no.")
    assert len(out) == 30, len(out)
    # Real refusal reasons are often vague or point at the wrong cause. Every third case (and the INSUFFICIENT ones) gets
    # a vague reason, every third+1 a misleading one, so the keyword baseline cannot read the answer from the wording.
    vague = ["System issue, try again later.", "Doctor is not available today.", "Come tomorrow.", "Not possible at this time."]
    misleading = {"REFERRAL": "Your card is not valid.", "ENTITLEMENT": "Pay a deposit first.", "LINKAGE": "Waiting for approval.",
                  "IMPROPER_CHARGE": "Documents are not complete.", "EMPANELMENT": "Referral is not accepted.",
                  "FORMS": "Hospital is not part of the scheme for this.", "ESCALATION_ONLY": "Documents do not match.",
                  "INSUFFICIENT_EVIDENCE": "Waiting for approval."}
    for i, o in enumerate(out):
        if i % 3 == 1:
            o["case"]["refusal_reason"] = vague[i % len(vague)]
        elif i % 3 == 2:
            o["case"]["refusal_reason"] = misleading[o["expected_blocker"]]
    for i, o in enumerate(out):
        o["split"] = "dev" if i in DEV else "test"
    return out


def build_fresh() -> list[dict]:
    return copy.deepcopy(build())
