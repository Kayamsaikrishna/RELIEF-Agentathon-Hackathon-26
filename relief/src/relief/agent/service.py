"""Public entry points: run_case, resume_case, get_result. Everything the API and the CLI need."""
from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from relief.agent.executor import ActionExecutor, RecordingExecutor
from relief.agent.graph import Deps, build_graph
from relief.config import Settings, get_settings
from relief.contracts.schemas import (BlockerFinding, CaseInput, CaseResult, CaseStatus, Decision, Evidence, Plan, TraceEvent,
                                      Verification)
from relief.llm.client import LLM, OllamaClient
from relief.tools import Registry, RulesKB, format_draft


class CaseExists(Exception):
    pass


class NoSuchCase(Exception):
    pass


class NotAwaitingApproval(Exception):
    pass


class Agent:
    def __init__(self, settings: Optional[Settings] = None, llm: Optional[LLM] = "auto", executor: Optional[ActionExecutor] = None,  # type: ignore[assignment]
                 kb: Optional[RulesKB] = None, registry: Optional[Registry] = None, tool_choice: str = "llm",
                 checkpoint_path: Optional[Path | str] = None):
        self.settings = settings or get_settings()
        self.settings.var_dir.mkdir(parents=True, exist_ok=True)
        if llm == "auto":
            llm = OllamaClient(self.settings)
        self.llm = llm
        self.kb = kb or RulesKB(self.settings)
        self.registry = registry or Registry.load(self.settings.registry_path)
        self.executor = executor or RecordingExecutor()
        path = str(checkpoint_path or self.settings.checkpoint_path)
        self._lock = threading.RLock()  # one graph call at a time on the shared checkpoint connection
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        deps = Deps(self.settings, self.kb, self.registry, self.llm, self.executor, tool_choice)
        self.graph = build_graph(deps, SqliteSaver(self._conn))
        # A second connection lets the screen read progress while a long run (model calls) holds the write lock.
        self._rconn = sqlite3.connect(path, check_same_thread=False)
        self.read_graph = build_graph(deps, SqliteSaver(self._rconn))

    # -------------------------------------------------------------- helpers
    def _cfg(self, case_id: str) -> dict:
        return {"configurable": {"thread_id": case_id}, "recursion_limit": 60}

    def exists(self, case_id: str) -> bool:
        return self.read_graph.get_state(self._cfg(case_id)).created_at is not None

    def run_case(self, case: CaseInput) -> CaseResult:
        if self.exists(case.case_id):
            raise CaseExists(case.case_id)
        with self._lock:
            self.graph.invoke({"case": case.model_dump(mode="json")}, self._cfg(case.case_id))
        return self.get_result(case.case_id)

    def resume_case(self, case_id: str, decision: Decision) -> CaseResult:
        with self._lock:
            snap = self.graph.get_state(self._cfg(case_id))
            if snap.created_at is None:
                raise NoSuchCase(case_id)
            if not snap.next or "human_gate" not in snap.next:
                raise NotAwaitingApproval(case_id)
            self.graph.invoke(Command(resume=decision.model_dump(mode="json")), self._cfg(case_id))
        return self.get_result(case_id)

    def get_result(self, case_id: str) -> CaseResult:
        snap = self.read_graph.get_state(self._cfg(case_id))
        if snap.created_at is None:
            raise NoSuchCase(case_id)
        s = snap.values
        if not s or "case" not in s:
            raise NoSuchCase(case_id)
        waiting = bool(snap.next and "human_gate" in snap.next and s.get("plan"))
        status = CaseStatus.AWAITING_APPROVAL if waiting else CaseStatus(s.get("status", "running"))
        findings = [BlockerFinding.model_validate(f) for f in s.get("findings", [])]
        plan = Plan.model_validate(s["plan"]) if s.get("plan") else None
        if plan and plan.drafts:
            plan.drafts = {k: format_draft(v) for k, v in plan.drafts.items()}
        ver = Verification.model_validate(s["verification"]) if s.get("verification") else None
        case = CaseInput.model_validate(s["case"])
        cited = list(dict.fromkeys(r for f in findings for r in f.rule_ids))
        if plan:
            cited += [i.rule_id for i in plan.checklist if i.rule_id and i.rule_id not in cited]
        passages = [self.kb.get(r) for r in cited if r in self.kb.ids()]
        return CaseResult(
            case_id=case_id, status=status, findings=findings, plan=plan, verification=ver,
            handover_missing=s.get("missing", []) if status == CaseStatus.HANDOVER else [],
            handover_reason=s.get("handover_reason", ""), emergency_notice=s.get("emergency_notice"),
            evidence=[Evidence.model_validate(e) for e in s.get("evidence", [])], rules_cited=passages,
            trace=[TraceEvent.model_validate(t) for t in s.get("trace", [])],
            decisions=[Decision.model_validate(d) for d in s.get("decisions", [])],
            llm_used=bool(s.get("llm_used")), model=self.settings.llm_model if s.get("llm_used") else None, synthetic=case.synthetic)

    def close(self) -> None:
        self._conn.close()
        self._rconn.close()
