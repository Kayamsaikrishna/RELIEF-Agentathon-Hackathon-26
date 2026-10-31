"""Referral check against the Karnataka referral rules (WHO 2025) and the benefit-package rules.

Conservative by design: where the source documents do not establish a rule, the answer is "unknown".
"""
from __future__ import annotations

from datetime import datetime, timezone

from relief.contracts.schemas import CaseInput, HospitalCheck, ReferralCheck

VALID_DAYS = 30


def check_referral(case: CaseInput, hospital: HospitalCheck) -> ReferralCheck:
    rules: list[str] = []
    tier = hospital.tier
    required = "unknown"
    why: list[str] = []

    if tier == "4A":
        required = "no"
        rules += ["WHO-4A-NO-REFERRAL", "WHO-EMERGENCY-DIRECT"]
        why.append("Emergency (tier 4A) procedures do not need a referral.")
    elif tier is None or hospital.hospital_type == "unknown":
        why.append("The tier or hospital type is not known, so the referral rule cannot be applied.")
    elif hospital.hospital_type == "private":
        if tier in ("2B", "3A"):
            required = "yes"
            rules += ["WHO-2B3A-REFERRAL"]
            why.append(f"Tier {tier} procedures are routed through referral and a private hospital is involved.")
        if hospital.reserved_for_public == "yes":
            required = "yes"
            rules += ["HBP-RESERVED-PUBLIC", "HBP-RESERVED-REFERRAL"]
            why.append("This package is reserved for public hospitals; a private hospital needs a referral from a public hospital.")
        if tier == "2A":
            why.append("Tier 2A procedures are provided only in government hospitals; a referral does not change that.")
    else:
        why.append("The source documents describe referral for private hospitals; the rule for a public hospital is not established here.")

    present = case.referral.present
    expired = "unknown"
    retro = "unknown"
    days = None
    if present == "yes" and case.referral.issued_on is not None:
        ref_date = case.admission_date or (case.as_of or datetime.now(timezone.utc)).date()
        days = (ref_date - case.referral.issued_on).days
        expired = "yes" if days > VALID_DAYS else "no"
        rules.append("WHO-REFERRAL-VALID-30D")
        if case.admission_date is not None:
            retro = "yes" if case.referral.issued_on > case.admission_date else "no"
            if retro == "yes":
                rules.append("WHO-RETROSPECTIVE-REFERRAL")
        if expired == "yes":
            why.append(f"The referral was issued {days} days before the reference date; the letter is valid for {VALID_DAYS} days.")
        if retro == "yes":
            why.append("The referral was issued after admission (retrospective).")
    dedup = list(dict.fromkeys(rules))
    return ReferralCheck(required=required, present=present, expired=expired, retrospective=retro,  # type: ignore[arg-type]
                         days_since_issue=days, tier=tier, rule_ids=dedup, explanation=" ".join(why))
