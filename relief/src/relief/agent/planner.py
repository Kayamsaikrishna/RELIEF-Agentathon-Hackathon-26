"""Build the plan from findings. Checklists, letters and hospital lists come from code and templates.
The model contributes at most one summary sentence (see prompts.py)."""
from __future__ import annotations

from typing import Optional

from relief.agent.context import CaseContext
from relief.contracts.schemas import Action, Blocker, BlockerFinding, ChecklistItem, Plan
from relief.tools.letters import render_letter
from relief.tools.registry import Registry
from relief.tools.rules_kb import RulesKB

REMIND_HOURS = 24


def _item(key: str, text: str, rule_id: Optional[str] = None, required: bool = True) -> ChecklistItem:
    return ChecklistItem(key=key, text=text, rule_id=rule_id, required=required)


def checklist_for(ctx: CaseContext, f: BlockerFinding) -> list[ChecklistItem]:
    b = f.blocker
    h, r, d = ctx.hospital, ctx.referral, ctx.docs_check
    hosp = h.hospital_name if h and h.hospital_name else ctx.case.hospital_id
    proc = h.procedure_name if h and h.procedure_name else ctx.case.procedure_code
    items: list[ChecklistItem] = []
    if b == Blocker.LINKAGE:
        fields = sorted({m.field for m in (ctx.record_check.mismatches if ctx.record_check else [])}) or ["the differing field"]
        items.append(_item("fix_record", f"Ask the beneficiary for a corrected document, or request a record correction, for: {', '.join(fields)}. "
                                         "Do not change the card data yourself.", "OPS-BIS-DOCUMENTS"))
        items.append(_item("recheck", "Compare the card and the corrected document again before submitting."))
    elif b == Blocker.ENTITLEMENT:
        items.append(_item("verify_bis", "Look up the beneficiary in the beneficiary identification system using Aadhaar or an alternative government ID "
                                         "and the ration card or an alternative family ID.", "OPS-BIS-DOCUMENTS"))
        items.append(_item("eligibility_channels", "If the lookup still returns no match, ask the call centre (14555) or the Am I Eligible service. "
                                                   "A person makes the decision.", "PMJAY-FLOW-ELIGIBILITY"))
    elif b == Blocker.EMPANELMENT:
        items.append(_item("verify_empanelment", f"Confirm with the State Health Agency whether {hosp} is empanelled for this specialty and may perform {proc}.",
                           "HBP-SPECIALTY-EMPANELMENT"))
        items.append(_item("alt_hospitals", "Consider the alternative hospitals listed in the draft. Check availability and empanelment with each before the patient travels.",
                           required=False))
    elif b == Blocker.REFERRAL:
        items.append(_item("get_referral", "Ask the referring public hospital's nodal officer to issue a valid referral letter through the online referral system. "
                                           "A letter is valid for 30 days.", "WHO-REFERRAL-NODAL-OFFICER"))
        if r is not None and r.retrospective == "yes":
            items.append(_item("retrospective", "The referral was issued after admission. Retrospective referrals are listed as not allowed; ask the nodal officer how to proceed.",
                               "WHO-RETROSPECTIVE-REFERRAL"))
        items.append(_item("choose_hospital", "The referral lists receiving hospitals ranked by proximity within 50 km; the patient may choose from that list.",
                           "WHO-REFERRAL-LIST-50KM", required=False))
    elif b == Blocker.FORMS:
        names = ", ".join(k.value.replace("_", " ") for k in (d.missing if d else [])) or "the missing documents"
        items.append(_item("complete_docs", f"Collect and add the missing documents: {names}.", "HBP-DOCS-VARY"))
        items.append(_item("resubmit", "Submit the pre-authorisation request once the file is complete.", "HBP-PREAUTH-REQUIRED"))
    elif b == Blocker.IMPROPER_CHARGE:
        items.append(_item("record_charge", "Write down the amount, the purpose, the date and who asked for it.", "OPS-NO-CHARGE"))
        items.append(_item("ask_basis", "Ask the hospital to state in writing whether an additional payment applies and whether it was told to the beneficiary in advance.",
                           "HBP-ADVANCE-DISCLOSURE"))
        items.append(_item("grievance", "If no disclosed additional payment applies, file a grievance on the grievance portal or call 14555.", "GRV-CHANNELS"))
    elif b == Blocker.ESCALATION_ONLY:
        items.append(_item("check_status", "Check the pre-authorisation status in the transaction system and note any query that was raised.", "OPS-PREAUTH-STEPS"))
        items.append(_item("grievance", "If it is still unresolved, file a grievance. Non-emergency grievances start at the district level; emergency grievances are handled at the state level.",
                           "GRV-NONSOS-15D"))
    return items


def alt_hospital_names(ctx: CaseContext, registry: Registry) -> list[str]:
    return [h.name for h in registry.alternatives(ctx.case.hospital_id, ctx.case.procedure_code)]


def build_plan(ctx: CaseContext, findings: list[BlockerFinding], summary: str, kb: RulesKB, registry: Registry,
               *, hours_label: Optional[str] = None) -> Plan:
    items: list[ChecklistItem] = []
    seen = set()
    for f in findings:
        for it in checklist_for(ctx, f):
            if it.key not in seen or it.key == "grievance":
                if it.key == "grievance" and any(x.key == "grievance" for x in items):
                    continue
                items.append(it)
                seen.add(it.key)
    items.append(_item("facilitator_review", "A facilitator checks every item and the cited rules before anything is sent."))

    h = ctx.hospital
    alt: list[str] = []
    if any(f.blocker in (Blocker.EMPANELMENT, Blocker.REFERRAL) for f in findings):
        alt = alt_hospital_names(ctx, registry)

    cited = list(dict.fromkeys(rid for f in findings for rid in f.rule_ids))
    rules = [r for r in kb.get_many(cited)]
    base = dict(case_id=ctx.case.case_id, patient_name=ctx.case.card.name, card_id=ctx.case.card.card_id,
                hospital_name=(h.hospital_name if h and h.hospital_name else ctx.case.hospital_id),
                procedure_name=(h.procedure_name if h and h.procedure_name else ctx.case.procedure_code))
    drafts: dict[str, str] = {}
    drafts["checklist"] = render_letter("checklist", {**base, "issue": findings[0].wording, "items": [i.model_dump() for i in items]})
    if alt:
        spec = h.specialty if h and h.specialty else "this specialty"
        state = h.state if h and h.state else "the state"
        drafts["hospital_list"] = render_letter("hospital_list", {
            "specialty": spec, "state": state, "note": "",
            "hospitals": [{"name": x.name, "type": x.type, "district": x.district}
                          for x in registry.alternatives(ctx.case.hospital_id, ctx.case.procedure_code)]})
    needs_letter = any(f.blocker in (Blocker.IMPROPER_CHARGE, Blocker.ESCALATION_ONLY) for f in findings)
    preauth_line = ""
    if ctx.case.preauth_submitted_at is not None:
        preauth_line = f"submitted {ctx.case.preauth_submitted_at.isoformat(timespec='minutes')}"
        if ctx.clock and ctx.clock.hours_elapsed is not None:
            preauth_line += f"; {ctx.clock.hours_elapsed:.1f} hours " + ("to a decision" if ctx.clock.decision_recorded else "without a recorded decision")
    if needs_letter:
        drafts["escalation"] = render_letter("escalation", {
            **base, "preauth_line": preauth_line, "refusal_reason": ctx.case.refusal_reason,
            "findings": [{"wording": f.wording} for f in findings], "summary": summary,
            "rules": [{"rule_id": r.rule_id, "text": r.text, "source_title": r.source_title, "section": r.section, "date": r.date} for r in rules]})

    actions: list[Action] = []
    if needs_letter:
        actions.append(Action(kind="send_escalation", payload={"draft": "escalation", "route": "grievance portal or helpline 14555",
                                                                "note": "Logged as prepared. A person sends it."}))
    actions.append(Action(kind="remind", payload={"after_hours": REMIND_HOURS, "text": f"Follow up on case {ctx.case.case_id}: {findings[0].blocker.value.replace('_', ' ').lower()}"}))
    return Plan(checklist=items, alt_hospitals=alt, letter_text=drafts.get("escalation"), drafts=drafts, actions=actions, summary=summary)
