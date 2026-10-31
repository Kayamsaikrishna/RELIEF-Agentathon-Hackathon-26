import pytest

from relief.agent.service import CaseExists, NotAwaitingApproval
from relief.contracts.schemas import Decision
from relief.llm.client import LLMOutputError, LLMUnavailable
from tests.conftest import ScriptedLLM, make_case
from relief.agent.service import Agent


def test_referral_case_runs_pauses_and_completes(agent):
    res = agent.run_case(make_case(case_id="A1", referral={"present": "no"}))
    assert res.status.value == "awaiting_approval" and res.main_blocker.value == "REFERRAL"
    assert res.findings[0].wording.startswith("Possible") and res.rules_cited and res.verification.passed
    assert not any(t.kind == "model" for t in res.trace) and res.llm_used is False
    done = agent.resume_case("A1", Decision(action="approve", decided_by="tester"))
    assert done.status.value == "completed" and done.decisions[0].decided_by == "tester"


def test_nothing_executes_before_approval(agent):
    agent.run_case(make_case(case_id="A2", referral={"present": "no"}))
    assert agent.executor.calls == []
    agent.resume_case("A2", Decision(action="reject"))
    assert agent.executor.calls == []


def test_reject_and_double_resume(agent):
    agent.run_case(make_case(case_id="A3", referral={"present": "no"}))
    assert agent.resume_case("A3", Decision(action="reject")).status.value == "rejected"
    with pytest.raises(NotAwaitingApproval):
        agent.resume_case("A3", Decision(action="approve"))


def test_duplicate_case_id(agent):
    agent.run_case(make_case(case_id="A4", referral={"present": "no"}))
    with pytest.raises(CaseExists):
        agent.run_case(make_case(case_id="A4"))


def test_edit_is_rechecked_and_saved(agent):
    res = agent.run_case(make_case(case_id="A5", referral={"present": "no"}))
    p = res.plan.model_copy(deep=True)
    p.checklist[0].text = "Ask the hospital desk for the referral letter and note the date."
    done = agent.resume_case("A5", Decision(action="edit", edited_plan=p))
    assert done.status.value == "completed" and done.plan.checklist[0].text.startswith("Ask the hospital desk")


def test_emergency_wording_hands_over_with_fixed_notice(agent):
    res = agent.run_case(make_case(case_id="A6", refusal_reason="Patient has severe chest pain and cannot breathe"))
    assert res.status.value == "handover" and res.emergency_notice and "112" in res.emergency_notice and res.plan is None


def test_insufficient_evidence_hands_over_with_missing_list(agent):
    res = agent.run_case(make_case(case_id="A7", hospital_id="H-901", documents=[]))
    assert res.status.value == "handover" and res.main_blocker.value == "INSUFFICIENT_EVIDENCE" and res.handover_missing


def test_payment_case_has_letter_and_grievance(agent):
    res = agent.run_case(make_case(case_id="A8", payment_request={"amount_inr": 5000, "purpose": "deposit", "wallet_exhausted": "no", "disclosed_in_advance": "no"}))
    assert res.main_blocker.value == "IMPROPER_CHARGE" and "escalation" in res.plan.drafts and "5,000" in res.plan.drafts["escalation"]


GOOD = {"ToolChoice": None}


def test_model_path_is_used_and_traced(settings, tmp_path):
    llm = ScriptedLLM({"SummaryOut": {"summary": "Ask the hospital for the referral letter before the next visit."}})
    a = Agent(settings, llm=llm, checkpoint_path=tmp_path / "m.sqlite")
    res = a.run_case(make_case(case_id="M1", referral={"present": "no"}))
    assert res.llm_used and res.plan.summary.startswith("Ask the hospital") and any(t.kind == "model" for t in res.trace)


@pytest.mark.parametrize("err", [LLMUnavailable("down"), LLMOutputError("bad json")])
def test_model_failure_falls_back_visibly(settings, tmp_path, err):
    llm = ScriptedLLM({"SummaryOut": err, "ToolChoice": err})
    a = Agent(settings, llm=llm, checkpoint_path=tmp_path / "f.sqlite")
    res = a.run_case(make_case(case_id="F1", referral={"present": "no"}))
    assert res.status.value == "awaiting_approval" and res.main_blocker.value == "REFERRAL"
    assert any(t.kind == "fallback" for t in res.trace)


def test_model_summary_with_forbidden_wording_is_discarded(settings, tmp_path):
    llm = ScriptedLLM({"SummaryOut": {"summary": "The patient is eligible and treatment is guaranteed."}})
    a = Agent(settings, llm=llm, checkpoint_path=tmp_path / "x.sqlite")
    res = a.run_case(make_case(case_id="X1", referral={"present": "no"}))
    assert "eligible" not in res.plan.summary and res.verification.passed
    assert any("forbidden" in t.input_summary for t in res.trace)


def test_model_cannot_skip_applicable_checks(settings, tmp_path):
    llm = ScriptedLLM({})  # every call raises KeyError-free validation failure -> fallback
    a = Agent(settings, llm=llm, checkpoint_path=tmp_path / "s.sqlite")
    res = a.run_case(make_case(case_id="S1"))
    tools = {t.tool for t in res.trace if t.kind == "tool"}
    assert {"lookup_hospital", "check_referral", "check_documents", "read_documents", "check_records"} <= tools


def test_state_survives_restart(settings, tmp_path):
    ck = tmp_path / "r.sqlite"
    a = Agent(settings, llm=None, checkpoint_path=ck)
    a.run_case(make_case(case_id="R1", referral={"present": "no"}))
    a.close()
    b = Agent(settings, llm=None, checkpoint_path=ck)
    assert b.resume_case("R1", Decision(action="approve")).status.value == "completed"
