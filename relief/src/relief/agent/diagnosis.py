"""Evidence to candidate blockers, in code. The model only ranks among these candidates."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from relief.agent.context import CaseContext
from relief.contracts.schemas import Blocker, Confidence

PRIORITY = [Blocker.EMPANELMENT, Blocker.REFERRAL, Blocker.LINKAGE, Blocker.ENTITLEMENT, Blocker.FORMS,
            Blocker.IMPROPER_CHARGE, Blocker.ESCALATION_ONLY]
EVIDENCE_TOOLS = {
    Blocker.LINKAGE: ["check_records", "read_documents"],
    Blocker.ENTITLEMENT: ["intake"],
    Blocker.EMPANELMENT: ["lookup_hospital"],
    Blocker.REFERRAL: ["check_referral", "lookup_hospital"],
    Blocker.FORMS: ["check_documents"],
    Blocker.IMPROPER_CHARGE: ["intake"],
    Blocker.ESCALATION_ONLY: ["preauth_clock", "intake"],
}
_ELIGIBILITY_WORDS = re.compile(r"eligib|not found|no record|card (is )?(not )?valid|invalid card|not registered|not covered|not a beneficiary", re.I)


@dataclass
class Candidate:
    blocker: Blocker
    strength: int  # 3 strong, 2 moderate, 1 weak
    wording: str
    rule_ids: list[str] = field(default_factory=list)


def _inr(x: float) -> str:
    return f"Rs {x:,.0f}"


def unknowns(ctx: CaseContext) -> list[str]:
    out: list[str] = []
    h = ctx.hospital
    if h is None or not h.found:
        out.append(f"hospital {ctx.case.hospital_id} was not found in the registry")
    if h is not None and h.package_listed != "yes":
        out.append(f"procedure code {ctx.case.procedure_code} was not found in the registry")
    if not ctx.case.documents:
        out.append("no documents were provided")
    elif ctx.record_check is not None and ctx.record_check.status == "unknown":
        out.append("no readable document could be compared with the card")
    if ctx.docs_check is not None and ctx.docs_check.status == "unknown":
        out.append("the required document list for this procedure is not known")
    if ctx.referral is not None and ctx.referral.required == "unknown":
        out.append("whether a referral is needed could not be established")
    return out


def build_candidates(ctx: CaseContext) -> list[Candidate]:
    c = ctx.case
    cands: list[Candidate] = []

    rc = ctx.record_check
    if rc is not None and rc.status == "mismatch":
        parts = []
        strong = False
        for m in rc.mismatches[:3]:
            strong = strong or m.kind == "different"
            sim = f", similarity {m.similarity:.0f}%" if m.similarity is not None else ""
            parts.append(f"{m.field} is '{m.card_value}' on the card but '{m.doc_value}' on document {m.doc_id}{sim}")
        cands.append(Candidate(Blocker.LINKAGE, 3 if strong else 2,
                               "Possible record mismatch: " + "; ".join(parts) + ". Requires verification.",
                               ["OPS-BIS-DOCUMENTS"]))

    if c.bis_status == "not_found":
        cands.append(Candidate(Blocker.ENTITLEMENT, 3,
                               "Possible entitlement not verified: the beneficiary lookup entered for this case returned no match. "
                               "Requires verification by a person; RELIEF does not decide eligibility.",
                               ["PMJAY-FLOW-ELIGIBILITY", "OPS-BIS-DOCUMENTS"]))
    elif c.bis_status == "unknown" and _ELIGIBILITY_WORDS.search(c.refusal_reason):
        cands.append(Candidate(Blocker.ENTITLEMENT, 2,
                               "Possible entitlement question: the hospital's reason refers to eligibility or the card, and no beneficiary "
                               "lookup was recorded. Requires verification by a person; RELIEF does not decide eligibility.",
                               ["PMJAY-FLOW-ELIGIBILITY", "OPS-BIS-DOCUMENTS"]))

    h = ctx.hospital
    if h is not None and h.found and h.package_listed == "yes":
        if h.hospital_type == "private" and h.tier == "2A":
            cands.append(Candidate(Blocker.EMPANELMENT, 3,
                                   f"Possible hospital-package mismatch: {h.procedure_name} is a tier 2A procedure, which statutory "
                                   f"scheme guidelines reserve for government hospitals, and {h.hospital_name} is private. Requires verification.",
                                   ["WHO-2A-GOVERNMENT", "HBP-RESERVED-PUBLIC"]))
        elif h.empanelled == "no":
            why = " ".join(n for n in h.notes if "not listed" in n or "not active" in n) or "the registry does not list it for this procedure"
            cands.append(Candidate(Blocker.EMPANELMENT, 3,
                                   f"Possible empanelment mismatch: {h.hospital_name}: {why} Requires verification.",
                                   ["HBP-SPECIALTY-EMPANELMENT", "HBP-BOOKING-NOT-AUTH"]))

    r = ctx.referral
    if r is not None and r.required == "yes":
        reasons = []
        if r.present == "no":
            reasons.append("no referral was provided")
        if r.expired == "yes":
            reasons.append(f"the referral is {r.days_since_issue} days old and its validity is 30 days")
        if r.retrospective == "yes":
            reasons.append("the referral was issued after admission")
        if reasons:
            cands.append(Candidate(Blocker.REFERRAL, 3,
                                   f"Possible referral problem: a referral appears to be needed for {h.procedure_name if h else 'this procedure'}, but "
                                   + "; ".join(reasons) + ". Requires verification.", r.rule_ids))
        elif r.present == "unknown":
            cands.append(Candidate(Blocker.REFERRAL, 2,
                                   "Possible missing referral: a referral appears to be needed and none has been recorded. Requires verification.",
                                   r.rule_ids))

    d = ctx.docs_check
    if d is not None and d.status == "incomplete" and c.documents:
        names = ", ".join(k.value.replace("_", " ") for k in d.missing)
        cands.append(Candidate(Blocker.FORMS, 3,
                               f"Possible incomplete pre-authorisation file: missing {names}. Requires verification.",
                               ["HBP-DOCS-VARY", "HBP-PREAUTH-REQUIRED"]))

    p = c.payment_request
    if p is not None and p.amount_inr > 0 and not (p.wallet_exhausted == "yes" and p.disclosed_in_advance == "yes"):
        strong = p.disclosed_in_advance != "yes"
        cands.append(Candidate(Blocker.IMPROPER_CHARGE, 3 if strong else 2,
                               f"Possible improper charge: the hospital asked for {_inr(p.amount_inr)} ({p.purpose}). The scheme is cashless unless an "
                               "additional payment applies and was disclosed in advance. Requires verification.",
                               ["HBP-CASHLESS", "HBP-ADVANCE-DISCLOSURE", "OPS-NO-CHARGE"]))

    k = ctx.clock
    if k is not None and k.hours_elapsed is not None and any(l.exceeded == "yes" for l in k.limits) and not k.decision_recorded:
        exceeded = [l for l in k.limits if l.exceeded == "yes"]
        txt = " and ".join(f"{l.limit_hours:g}-hour ({l.rule_id})" for l in exceeded)
        cands.append(Candidate(Blocker.ESCALATION_ONLY, 3,
                               f"Possible delay: pre-authorisation has been pending {k.hours_elapsed:.1f} hours, beyond the {txt} period. "
                               "Requires verification of the status in the transaction system.",
                               [l.rule_id for l in exceeded] + ["GRV-NONSOS-15D", "GRV-CHANNELS"]))
    return cands


def clean_checks(ctx: CaseContext) -> bool:
    """True when every check ran and found nothing inconsistent (the 'implementation gap' situation)."""
    h = ctx.hospital
    return bool(
        ctx.case.documents and ctx.record_check is not None and ctx.record_check.status == "consistent"
        and h is not None and h.found and h.empanelled == "yes" and h.hospital_type != "unknown"
        and ctx.referral is not None and ctx.referral.required in ("no", "yes")
        and ctx.docs_check is not None and ctx.docs_check.status == "complete"
    )


def escalation_gap_candidate() -> Candidate:
    return Candidate(Blocker.ESCALATION_ONLY, 2,
                     "Possible implementation gap: the checks found no inconsistency in the card, documents, hospital, referral or file. "
                     "A person may need to review the refusal through the grievance channels. Requires verification.",
                     ["GRV-LEVELS", "GRV-CHANNELS", "GRV-NONSOS-15D"])


def confidence_for(c: Candidate, n_strong: int) -> Confidence:
    if c.strength >= 3 and n_strong == 1:
        return Confidence.HIGH
    if c.strength >= 2:
        return Confidence.MEDIUM
    return Confidence.LOW


def fallback_order(cands: list[Candidate]) -> list[Candidate]:
    return sorted(cands, key=lambda c: (-c.strength, PRIORITY.index(c.blocker)))
