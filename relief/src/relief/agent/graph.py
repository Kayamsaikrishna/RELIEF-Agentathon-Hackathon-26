"""The LangGraph agent.

    intake -> choose_tool <-> run_tool -> retrieve -> diagnose -> (gate) -> plan -> verify -> human_gate -> act_track -> finalize
                                                          \\-> finalize (hand over)        \\-> plan (revise, max 2) / hand over

Code decides every fact. The local model (when reachable) only orders the checks, ranks the candidate
blockers and writes one summary sentence; each use is validated and has a visible fallback.
"""
from __future__ import annotations

import json
import logging
import operator
import sqlite3
from dataclasses import dataclass
from typing import Annotated, Any, Optional, TypedDict

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from relief.agent import diagnosis as dx
from relief.agent import prompts
from relief.agent.context import CaseContext
from relief.agent.executor import ActionExecutor
from relief.agent.planner import build_plan, checklist_for
from relief.agent.safety import EMERGENCY_NOTICE, forbidden_phrases, has_emergency_language
from relief.agent.verifier import verify
from relief.config import Settings
from relief.contracts.schemas import (Blocker, BlockerFinding, CaseInput, CaseStatus, Confidence, Decision, Evidence, Plan,
                                      TraceEvent, Verification)
from relief.llm.client import LLM, LLMOutputError, LLMUnavailable
from relief.tools import (Registry, RulesKB, check_documents, check_records, check_referral, preauth_clock, read_documents)

log = logging.getLogger(__name__)


class AgentState(TypedDict, total=False):
    case: dict
    doc_fields: list
    record_check: dict
    hospital: dict
    referral: dict
    docs_check: dict
    clock: dict
    evidence: Annotated[list, operator.add]
    trace: Annotated[list, operator.add]
    tools_done: Annotated[list, operator.add]
    decisions: Annotated[list, operator.add]
    steps: int
    next_tool: str
    findings: list
    missing: list
    summary: str
    plan: dict
    verification: dict
    revisions: int
    issues: list
    status: str
    handover_reason: str
    emergency_notice: str
    outcomes: list
    llm_used: bool


@dataclass
class Deps:
    settings: Settings
    kb: RulesKB
    registry: Registry
    llm: Optional[LLM]
    executor: ActionExecutor
    tool_choice: str = "llm"  # "llm" or "fixed"


def _t(node: str, kind: str, inp: str = "", out: str = "", tool: Optional[str] = None) -> dict:
    return TraceEvent(node=node, tool=tool, kind=kind, input_summary=inp[:300], output_summary=out[:500]).model_dump(mode="json")  # type: ignore[arg-type]


def _ev(state: dict, tool: str, summary: str, data: dict, rule_ids: Optional[list[str]] = None) -> dict:
    n = len(state.get("evidence", [])) + 1
    return Evidence(evidence_id=f"E{n}", tool=tool, summary=summary[:500], data=data, rule_ids=rule_ids or []).model_dump(mode="json")


TOOL_ORDER = ["read_documents", "lookup_hospital", "check_records", "check_referral", "check_documents", "preauth_clock"]
PREREQ = {"check_records": ["read_documents"], "check_referral": ["lookup_hospital"], "check_documents": ["lookup_hospital", "check_referral"]}


def applicable_tools(case: CaseInput) -> list[str]:
    tools = ["lookup_hospital", "check_referral", "check_documents"]
    if case.documents:
        tools = ["read_documents", "check_records"] + tools
    if case.preauth_submitted_at is not None:
        tools.append("preauth_clock")
    return [t for t in TOOL_ORDER if t in tools]


def eligible_tools(case: CaseInput, done: list[str]) -> list[str]:
    return [t for t in applicable_tools(case) if t not in done and all(p in done or p not in applicable_tools(case) for p in PREREQ.get(t, []))]


def build_graph(deps: Deps, checkpointer: Optional[SqliteSaver] = None):
    kb, registry, llm = deps.kb, deps.registry, deps.llm

    # ------------------------------------------------------------------ model helper
    def ask(state: dict, node: str, system: str, user: str, schema):
        """Call the model; return (reply or None, trace events, llm_used flag)."""
        if llm is None:
            return None, [_t(node, "fallback", "model not configured", "used the rule-based fallback")], False
        try:
            reply = llm.chat_json(system, user, schema)
            return reply, [_t(node, "model", user[:200], json.dumps(reply.model_dump(), default=str)[:300])], True
        except LLMUnavailable as exc:
            log.warning("model unavailable: %s", exc)
            return None, [_t(node, "fallback", "model unavailable", "The local model could not be reached; used the rule-based fallback.")], False
        except LLMOutputError as exc:
            log.warning("model output invalid: %s", exc)
            return None, [_t(node, "fallback", "model reply invalid", "The model's reply was not valid; used the rule-based fallback.")], False

    # ------------------------------------------------------------------ nodes
    def intake(state: AgentState) -> dict:
        case = CaseInput.model_validate(state["case"])
        ev = _ev(state, "intake", "Case entered by the facilitator", {
            "bis_status": case.bis_status, "refusal_reason": case.refusal_reason, "referral": case.referral.model_dump(mode="json"),
            "payment_request": case.payment_request.model_dump(mode="json") if case.payment_request else None,
            "admission_date": case.admission_date.isoformat() if case.admission_date else None,
            "documents": [d.kind.value for d in case.documents]})
        out: dict[str, Any] = {"evidence": [ev], "steps": 0, "revisions": 0, "status": CaseStatus.RUNNING.value,
                               "trace": [_t("intake", "code", f"case {case.case_id}", f"{len(case.documents)} documents; synthetic={case.synthetic}")]}
        if has_emergency_language(case.refusal_reason, case.notes):
            out.update(status=CaseStatus.HANDOVER.value, emergency_notice=EMERGENCY_NOTICE,
                       handover_reason="The case mentions a possible medical emergency.",
                       missing=[], trace=out["trace"] + [_t("intake", "safety", "emergency wording found", "stopped; fixed emergency notice returned")])
        return out

    def after_intake(state: AgentState) -> str:
        return "finalize" if state.get("emergency_notice") else "choose_tool"

    def choose_tool(state: AgentState) -> dict:
        case = CaseInput.model_validate(state["case"])
        done = state.get("tools_done", [])
        elig = eligible_tools(case, done)
        if not elig:
            return {"next_tool": "retrieve"}
        if len(elig) == 1 or deps.tool_choice == "fixed":
            return {"next_tool": elig[0], "trace": [_t("choose_tool", "code", f"eligible: {', '.join(elig)}", f"next: {elig[0]}")]}
        schema = prompts.tool_choice_schema(elig)
        user = json.dumps({"hospital_reason": case.refusal_reason, "done": done,
                           "allowed": {t: prompts.TOOL_HELP[t] for t in elig}}, indent=0)
        reply, trace, used = ask(state, "choose_tool", prompts.TOOL_CHOICE_SYSTEM, user, schema)
        pick = reply.tool if reply is not None else elig[0]
        out: dict[str, Any] = {"next_tool": pick, "trace": trace}
        if used:
            out["llm_used"] = True
        return out

    def route_after_choice(state: AgentState) -> str:
        return "retrieve" if state["next_tool"] == "retrieve" else "run_tool"

    def run_tool(state: AgentState) -> dict:
        tool = state["next_tool"]
        ctx = CaseContext.from_state(state)
        case = ctx.case
        upd: dict[str, Any] = {}
        if tool == "read_documents":
            fields = read_documents(case.documents)
            upd["doc_fields"] = [f.model_dump(mode="json") for f in fields]
            by = {"ok": 0, "partial": 0, "unreadable": 0}
            for f in fields:
                by[f.status] += 1
            summary = f"Read {len(fields)} documents: {by['ok']} ok, {by['partial']} partial, {by['unreadable']} unreadable."
            ev = _ev(state, tool, summary, {"documents": upd["doc_fields"]})
        elif tool == "lookup_hospital":
            h = registry.lookup_hospital(case.hospital_id, case.procedure_code)
            upd["hospital"] = h.model_dump(mode="json")
            summary = (f"{h.hospital_name or case.hospital_id}: empanelled={h.empanelled}, tier={h.tier}, type={h.hospital_type}, "
                       f"registry {h.registry_version}.")
            ev = _ev(state, tool, summary, upd["hospital"])
        elif tool == "check_records":
            rc = check_records(case.card, ctx.doc_fields)
            upd["record_check"] = rc.model_dump(mode="json")
            summary = f"Records {rc.status}: {len(rc.mismatches)} difference(s) in {rc.compared_fields} comparisons."
            ev = _ev(state, tool, summary, upd["record_check"], ["OPS-BIS-DOCUMENTS"] if rc.mismatches else [])
        elif tool == "check_referral":
            r = check_referral(case, ctx.hospital)  # type: ignore[arg-type]
            upd["referral"] = r.model_dump(mode="json")
            summary = f"Referral required={r.required}, present={r.present}, expired={r.expired}. {r.explanation}"
            ev = _ev(state, tool, summary, upd["referral"], r.rule_ids)
        elif tool == "check_documents":
            d = check_documents(case, ctx.hospital, ctx.referral, registry)  # type: ignore[arg-type]
            upd["docs_check"] = d.model_dump(mode="json")
            summary = f"Documents {d.status}; missing: {', '.join(k.value for k in d.missing) or 'none'}."
            ev = _ev(state, tool, summary, upd["docs_check"], ["HBP-DOCS-VARY"] if d.missing else [])
        elif tool == "preauth_clock":
            c = preauth_clock(case)
            upd["clock"] = c.model_dump(mode="json")
            ev = _ev(state, tool, c.explanation, upd["clock"], [l.rule_id for l in c.limits if l.exceeded == "yes"])
        else:  # pragma: no cover
            raise ValueError(tool)
        upd.update(evidence=[ev], tools_done=[tool], steps=state.get("steps", 0) + 1,
                   trace=[_t("run_tool", "tool", tool, ev["summary"], tool=tool)])
        return upd

    def retrieve(state: AgentState) -> dict:
        ctx = CaseContext.from_state(state)
        parts = [ctx.case.refusal_reason]
        for e in state.get("evidence", []):
            if e["tool"] != "intake":
                parts.append(e["summary"])
        query = " ".join(parts)[:600]
        try:
            hits = kb.search(query, k=5)
            summary = "Related rules: " + ", ".join(h.rule_id for h in hits) if hits else "No related rules found."
            data = {"rules": [{"rule_id": h.rule_id, "score": h.score} for h in hits]}
            ev = _ev(state, "search_rules", summary, data, [])
            trace = [_t("retrieve", "tool", query[:150], summary, tool="search_rules")]
        except Exception as exc:  # embedding model or index missing: say so, keep going
            log.exception("rule search failed")
            ev = _ev(state, "search_rules", f"Rule search unavailable: {exc}", {}, [])
            trace = [_t("retrieve", "error", "rule search", f"unavailable: {exc}; cited rules still come from code")]
        return {"evidence": [ev], "trace": trace}

    def diagnose(state: AgentState) -> dict:
        ctx = CaseContext.from_state(state)
        cands = dx.build_candidates(ctx)
        trace = [_t("diagnose", "code", f"{len(ctx.case.documents)} documents, {len(state.get('evidence', []))} evidence items",
                    f"{len(cands)} candidate blocker(s): {', '.join(c.blocker.value for c in cands) or 'none'}")]
        used = False
        if not cands:
            if dx.clean_checks(ctx):
                cands = [dx.escalation_gap_candidate()]
                trace.append(_t("diagnose", "code", "all checks consistent", "implementation-gap candidate (escalation only)"))
            else:
                missing = dx.unknowns(ctx) or ["no inconsistency was found, but the checks could not all be completed"]
                f = BlockerFinding(blocker=Blocker.INSUFFICIENT_EVIDENCE, confidence=Confidence.LOW, evidence_ids=[],
                                   rule_ids=[], wording="Not enough evidence to name a blocker. A person needs to supply: " + "; ".join(missing) + ".")
                return {"findings": [f.model_dump(mode="json")], "missing": missing, "trace": trace + [_t("diagnose", "gate", "no candidate", "hand over")]}
        ordered = dx.fallback_order(cands)
        strong = [c for c in ordered if c.strength >= 2]
        if len(strong) >= 2:
            names = [c.blocker.value for c in strong]
            schema = prompts.ranking_schema(names)
            user = json.dumps({"hospital_reason": ctx.case.refusal_reason,
                               "candidates": [{"blocker": c.blocker.value, "finding": c.wording} for c in strong]}, indent=0)
            reply, tr, used = ask(state, "diagnose", prompts.RANKING_SYSTEM, user, schema)
            trace += tr
            if reply is not None:
                order = [x for x in reply.order if x in names]
                if sorted(order) == sorted(names) and len(set(order)) == len(order):
                    byname = {c.blocker.value: c for c in strong}
                    ordered = [byname[n] for n in order] + [c for c in ordered if c.blocker.value not in names]
                else:
                    trace.append(_t("diagnose", "fallback", "model ranking not a permutation", "used the rule-based order"))
        n_strong = len([c for c in ordered if c.strength >= 3])
        evid = {e["tool"]: e["evidence_id"] for e in state.get("evidence", [])}
        findings = []
        for c in ordered:
            ids = [evid[t] for t in dx.EVIDENCE_TOOLS[c.blocker] if t in evid]
            findings.append(BlockerFinding(blocker=c.blocker, confidence=dx.confidence_for(c, n_strong), evidence_ids=ids,
                                           rule_ids=list(dict.fromkeys(c.rule_ids)), wording=c.wording,
                                           source="model" if used else "rules"))
        out: dict[str, Any] = {"findings": [f.model_dump(mode="json") for f in findings], "missing": [], "trace": trace}
        if used:
            out["llm_used"] = True
        return out

    def after_diagnose(state: AgentState) -> str:
        top = state["findings"][0]
        if top["blocker"] == Blocker.INSUFFICIENT_EVIDENCE.value:
            return "handover_insufficient"
        if top["confidence"] == Confidence.LOW.value:
            return "handover_low"
        return "plan"

    def handover_insufficient(state: AgentState) -> dict:
        return {"status": CaseStatus.HANDOVER.value, "handover_reason": "Not enough evidence to name a blocker.",
                "trace": [_t("handover", "gate", "insufficient evidence", "; ".join(state.get("missing", []))[:400])]}

    def handover_low(state: AgentState) -> dict:
        f = state["findings"][0]
        return {"status": CaseStatus.HANDOVER.value, "missing": ["Confirm: " + f["wording"]],
                "handover_reason": "Confidence is low; a person should review before any plan is made.",
                "trace": [_t("handover", "gate", "low confidence", f["wording"][:300])]}

    def plan_node(state: AgentState) -> dict:
        ctx = CaseContext.from_state(state)
        findings = [BlockerFinding.model_validate(f) for f in state["findings"]]
        revising = state.get("revisions", 0) > 0
        summary = ""
        trace: list = []
        used = False
        if not revising:
            first = findings[0].wording
            user = json.dumps({"main_finding": first, "next_steps": [i.text for i in checklist_for(ctx, findings[0])]}, indent=0)
            reply, tr, used = ask(state, "plan", prompts.SUMMARY_SYSTEM, user, prompts.SummaryOut)
            trace += tr
            if reply is not None and not forbidden_phrases(reply.summary):
                summary = reply.summary.strip()
            elif reply is not None:
                trace.append(_t("plan", "fallback", "model summary contained forbidden wording", "used the rule-based summary"))
        if not summary:
            summary = "Next step: " + checklist_for(ctx, findings[0])[0].text
        plan = build_plan(ctx, findings, summary, kb, registry)
        trace.append(_t("plan", "code", f"{len(findings)} finding(s)", f"{len(plan.checklist)} checklist items; drafts: {', '.join(plan.drafts)}; actions: {', '.join(a.kind for a in plan.actions)}"))
        out: dict[str, Any] = {"plan": plan.model_dump(mode="json"), "summary": summary, "trace": trace}
        if used:
            out["llm_used"] = True
        return out

    def verify_node(state: AgentState) -> dict:
        ctx = CaseContext.from_state(state)
        findings = [BlockerFinding.model_validate(f) for f in state["findings"]]
        plan = Plan.model_validate(state["plan"])
        attempts = state.get("revisions", 0) + 1
        v = verify(plan, findings, ctx, {e["evidence_id"] for e in state.get("evidence", [])}, kb, attempts)
        trace = [_t("verify", "code", f"attempt {attempts}", "passed" if v.passed else "failed: " + "; ".join(v.issues)[:400])]
        return {"verification": v.model_dump(mode="json"), "issues": v.issues, "revisions": attempts if not v.passed else state.get("revisions", 0), "trace": trace}

    def after_verify(state: AgentState) -> str:
        v = Verification.model_validate(state["verification"])
        if v.passed:
            return "human_gate"
        return "plan" if state.get("revisions", 0) <= deps.settings.max_revisions else "handover_verify"

    def handover_verify(state: AgentState) -> dict:
        return {"status": CaseStatus.HANDOVER.value, "missing": state.get("issues", []),
                "handover_reason": "The plan did not pass the checks after revision, so a person should take over.",
                "trace": [_t("handover", "gate", "verification failed", "; ".join(state.get("issues", []))[:400])]}

    def human_gate(state: AgentState) -> dict:
        decision_raw = interrupt({"case_id": state["case"]["case_id"], "plan": state["plan"], "findings": state["findings"],
                                  "verification": state["verification"]})
        d = Decision.model_validate(decision_raw)
        trace = [_t("human_gate", "gate", f"decided by {d.decided_by}", d.action + (f": {d.note}" if d.note else ""))]
        out: dict[str, Any] = {"decisions": [d.model_dump(mode="json")], "trace": trace}
        if d.action == "reject":
            out["status"] = CaseStatus.REJECTED.value
        else:
            if d.action == "edit" and d.edited_plan is not None:
                ctx = CaseContext.from_state(state)
                findings = [BlockerFinding.model_validate(f) for f in state["findings"]]
                v = verify(d.edited_plan, findings, ctx, {e["evidence_id"] for e in state.get("evidence", [])}, kb, state.get("revisions", 0) + 1)
                out["plan"] = d.edited_plan.model_dump(mode="json")
                out["verification"] = v.model_dump(mode="json")
                out["trace"] = trace + [_t("human_gate", "code", "edited plan re-checked", "passed" if v.passed else "warnings: " + "; ".join(v.issues)[:300])]
            out["status"] = CaseStatus.APPROVED.value
        return out

    def after_gate(state: AgentState) -> str:
        return "act_track" if state.get("status") == CaseStatus.APPROVED.value else "finalize"

    def act_track(state: AgentState) -> dict:
        case = CaseInput.model_validate(state["case"])
        plan = Plan.model_validate(state["plan"])
        who = state["decisions"][-1].get("decided_by", "facilitator")
        outcomes = deps.executor.execute(case, plan, who)
        return {"status": CaseStatus.COMPLETED.value, "outcomes": [o.model_dump() for o in outcomes],
                "trace": [_t("act_track", "tool", ", ".join(a.kind for a in plan.actions), "; ".join(f"{o.kind}: {o.detail}" for o in outcomes)[:400])]}

    def finalize(state: AgentState) -> dict:
        return {}

    g = StateGraph(AgentState)
    for name, fn in [("intake", intake), ("choose_tool", choose_tool), ("run_tool", run_tool), ("retrieve", retrieve), ("diagnose", diagnose),
                     ("handover_insufficient", handover_insufficient), ("handover_low", handover_low), ("plan", plan_node),
                     ("verify", verify_node), ("handover_verify", handover_verify), ("human_gate", human_gate), ("act_track", act_track),
                     ("finalize", finalize)]:
        g.add_node(name, fn)
    g.add_edge(START, "intake")
    g.add_conditional_edges("intake", after_intake, {"finalize": "finalize", "choose_tool": "choose_tool"})
    g.add_conditional_edges("choose_tool", route_after_choice, {"run_tool": "run_tool", "retrieve": "retrieve"})
    g.add_edge("run_tool", "choose_tool")
    g.add_edge("retrieve", "diagnose")
    g.add_conditional_edges("diagnose", after_diagnose, {"plan": "plan", "handover_insufficient": "handover_insufficient", "handover_low": "handover_low"})
    g.add_edge("handover_insufficient", "finalize")
    g.add_edge("handover_low", "finalize")
    g.add_edge("plan", "verify")
    g.add_conditional_edges("verify", after_verify, {"human_gate": "human_gate", "plan": "plan", "handover_verify": "handover_verify"})
    g.add_edge("handover_verify", "finalize")
    g.add_conditional_edges("human_gate", after_gate, {"act_track": "act_track", "finalize": "finalize"})
    g.add_edge("act_track", "finalize")
    g.add_edge("finalize", END)
    return g.compile(checkpointer=checkpointer or SqliteSaver(sqlite3.connect(":memory:", check_same_thread=False)))
