"""Verifier: checks written in code. A plan that fails goes back for revision, then to a person."""
from __future__ import annotations

import re
from typing import Iterable

from relief.agent.context import CaseContext
from relief.agent.safety import forbidden_phrases
from relief.contracts.schemas import Blocker, BlockerFinding, Plan, Verification
from relief.tools.rules_kb import RulesKB

REQUIRED_KEYS: dict[Blocker, list[str]] = {
    Blocker.LINKAGE: ["fix_record"],
    Blocker.ENTITLEMENT: ["verify_bis"],
    Blocker.EMPANELMENT: ["verify_empanelment"],
    Blocker.REFERRAL: ["get_referral"],
    Blocker.FORMS: ["complete_docs"],
    Blocker.IMPROPER_CHARGE: ["record_charge", "grievance"],
    Blocker.ESCALATION_ONLY: ["check_status", "grievance"],
    Blocker.INSUFFICIENT_EVIDENCE: [],
}
LETTER_BLOCKERS = {Blocker.IMPROPER_CHARGE, Blocker.ESCALATION_ONLY}
_RULE_TOKEN = re.compile(r"\b(?:CAG|HBP|OPS|WHO|GRV|PMJAY)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")


def _texts(plan: Plan, findings: Iterable[BlockerFinding]) -> list[str]:
    out = [plan.summary] + [i.text for i in plan.checklist] + list(plan.drafts.values()) + [f.wording for f in findings]
    if plan.letter_text:
        out.append(plan.letter_text)
    return [t for t in out if t]


def verify(plan: Plan, findings: list[BlockerFinding], ctx: CaseContext, evidence_ids: set[str], kb: RulesKB,
           attempts: int = 0) -> Verification:
    issues: list[str] = []
    known = kb.ids()

    # 1. citations
    cit_ok = True
    for f in findings:
        if f.blocker != Blocker.INSUFFICIENT_EVIDENCE:
            if not f.evidence_ids:
                cit_ok = False
                issues.append(f"{f.blocker.value}: finding has no evidence")
            if not f.rule_ids:
                cit_ok = False
                issues.append(f"{f.blocker.value}: finding cites no rule")
        for e in f.evidence_ids:
            if e not in evidence_ids:
                cit_ok = False
                issues.append(f"{f.blocker.value}: unknown evidence id {e}")
        for rid in f.rule_ids:
            if rid not in known:
                cit_ok = False
                issues.append(f"{f.blocker.value}: unknown rule id {rid}")
    for it in plan.checklist:
        if it.rule_id and it.rule_id not in known:
            cit_ok = False
            issues.append(f"checklist item {it.key}: unknown rule id {it.rule_id}")
    for name, text in plan.drafts.items():
        for tok in set(_RULE_TOKEN.findall(text)):
            if tok not in known:
                cit_ok = False
                issues.append(f"draft {name}: cites unknown rule {tok}")
    if "escalation" in plan.drafts:
        for rid in dict.fromkeys(r for f in findings for r in f.rule_ids):
            rule = kb.get(rid)
            if rule and rule.text not in plan.drafts["escalation"]:
                cit_ok = False
                issues.append(f"escalation letter does not quote rule {rid} as stored")

    # 2. required fields
    fields_ok = True
    keys = {i.key for i in plan.checklist}
    for f in findings:
        for k in REQUIRED_KEYS.get(f.blocker, []):
            if k not in keys:
                fields_ok = False
                issues.append(f"missing checklist step '{k}' for {f.blocker.value}")
    if any(f.blocker in LETTER_BLOCKERS for f in findings):
        letter = plan.drafts.get("escalation") or ""
        if not letter:
            fields_ok = False
            issues.append("escalation letter is missing")
        else:
            h = ctx.hospital
            must = {"patient name": ctx.case.card.name, "card id": ctx.case.card.card_id,
                    "procedure": (h.procedure_name if h and h.procedure_name else ctx.case.procedure_code)}
            for label, val in must.items():
                if val and val not in letter:
                    fields_ok = False
                    issues.append(f"escalation letter does not contain the {label}")
    if "checklist" not in plan.drafts:
        fields_ok = False
        issues.append("checklist draft is missing")

    # 3. safety
    hits: list[str] = []
    for t in _texts(plan, findings):
        hits += forbidden_phrases(t)
    hits = list(dict.fromkeys(hits))
    safety_ok = not hits
    for f in findings:
        if not (f.wording.startswith("Possible") or f.wording.startswith("Not enough evidence")):
            safety_ok = False
            issues.append(f"finding wording for {f.blocker.value} must start with 'Possible'")
    if hits:
        issues.append("forbidden wording found: " + "; ".join(hits))

    return Verification(citations_ok=cit_ok, fields_ok=fields_ok, safety_ok=safety_ok, forbidden_phrases=hits,
                        issues=issues, attempts=attempts)
