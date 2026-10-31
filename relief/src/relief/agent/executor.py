"""What happens after a person approves. The agent never executes anything before that point."""
from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from relief.contracts.schemas import CaseInput, Plan


class ActionOutcome(BaseModel):
    kind: str
    ok: bool
    detail: str


class ActionExecutor(Protocol):
    def execute(self, case: CaseInput, plan: Plan, decided_by: str) -> list[ActionOutcome]: ...


class RecordingExecutor:
    """Executor with no outside effects: records what would have been done. Used by the command line,
    the evaluation harness and tests. The API uses the app's executor (simulator and reminders)."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    def execute(self, case: CaseInput, plan: Plan, decided_by: str) -> list[ActionOutcome]:
        self.calls.append((case.case_id, [a.kind for a in plan.actions]))
        return [ActionOutcome(kind=a.kind, ok=True, detail="recorded only (no external system)") for a in plan.actions]
