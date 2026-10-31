from relief.agent.context import CaseContext
from relief.agent.service import Agent
from relief.agent.verifier import verify
from relief.contracts.schemas import ChecklistItem
from tests.conftest import make_case


def _ready(agent):
    res = agent.run_case(make_case(referral={"present": "no"}, case_id="V1"))
    assert res.status.value == "awaiting_approval"
    state = agent.graph.get_state({"configurable": {"thread_id": "V1"}}).values
    return res, CaseContext.from_state(state), {e["evidence_id"] for e in state["evidence"]}


def test_good_plan_passes(agent):
    res, ctx, ev = _ready(agent)
    v = verify(res.plan, res.findings, ctx, ev, agent.kb)
    assert v.passed, v.issues


def test_unknown_rule_id_is_caught(agent):
    res, ctx, ev = _ready(agent)
    res.findings[0].rule_ids.append("MADE-UP-RULE")
    v = verify(res.plan, res.findings, ctx, ev, agent.kb)
    assert not v.citations_ok and any("MADE-UP-RULE" in i for i in v.issues)


def test_missing_required_item_is_caught(agent):
    res, ctx, ev = _ready(agent)
    res.plan.checklist = [i for i in res.plan.checklist if i.key != "get_referral"]
    v = verify(res.plan, res.findings, ctx, ev, agent.kb)
    assert not v.fields_ok


def test_forbidden_phrases_are_caught(agent):
    res, ctx, ev = _ready(agent)
    for bad in ["The patient is eligible for treatment.", "Treatment is guaranteed.", "Take 500 mg of paracetamol."]:
        res.plan.summary = bad
        v = verify(res.plan, res.findings, ctx, ev, agent.kb)
        assert not v.safety_ok, bad


def test_unknown_evidence_id_is_caught(agent):
    res, ctx, ev = _ready(agent)
    res.findings[0].evidence_ids.append("E99")
    assert not verify(res.plan, res.findings, ctx, ev, agent.kb).citations_ok
