"""Executes approved actions against the simulator and the reminder table. Runs only after a human decision."""
from __future__ import annotations

from relief.agent.executor import ActionOutcome
from relief.app import portal
from relief.app.db import Database
from relief.contracts.schemas import CaseInput, Plan


class AppExecutor:
    def __init__(self, db: Database):
        self.db = db

    def execute(self, case: CaseInput, plan: Plan, decided_by: str) -> list[ActionOutcome]:
        out: list[ActionOutcome] = []
        for a in plan.actions:
            if a.kind == "submit_preauth":
                r = portal.submit(case, {**a.payload, "hospital_id": case.hospital_id, "procedure_code": case.procedure_code, "card_id": case.card.card_id})
                if r["accepted"]:
                    self.db.add_submission(case.case_id, a.kind, r["reference"], a.payload)
                    out.append(ActionOutcome(kind=a.kind, ok=True, detail=f"{r['label']}; reference {r['reference']}"))
                else:
                    out.append(ActionOutcome(kind=a.kind, ok=False, detail="; ".join(r["errors"])))
            elif a.kind == "send_escalation":
                ref = f"DRAFT-{case.case_id}"
                self.db.add_submission(case.case_id, a.kind, ref, a.payload, simulated=True)
                out.append(ActionOutcome(kind=a.kind, ok=True, detail="Escalation letter saved for the facilitator to send by the grievance channel; nothing was sent automatically."))
            elif a.kind == "remind":
                hours = float(a.payload.get("after_hours", 24))
                self.db.add_reminder(case.case_id, hours, str(a.payload.get("text", "Check the case status.")))
                out.append(ActionOutcome(kind=a.kind, ok=True, detail=f"Reminder set for {hours:g} hours from now."))
        return out
