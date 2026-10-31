"""Typed view over the plain-dict graph state."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from relief.contracts.schemas import (CaseInput, ClockResult, DocCompleteness, DocFields, HospitalCheck,
                                      RecordCheck, ReferralCheck)


@dataclass
class CaseContext:
    case: CaseInput
    doc_fields: list[DocFields] = field(default_factory=list)
    record_check: Optional[RecordCheck] = None
    hospital: Optional[HospitalCheck] = None
    referral: Optional[ReferralCheck] = None
    docs_check: Optional[DocCompleteness] = None
    clock: Optional[ClockResult] = None

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "CaseContext":
        def m(key: str, model):
            v = state.get(key)
            return model.model_validate(v) if v else None

        return cls(
            case=CaseInput.model_validate(state["case"]),
            doc_fields=[DocFields.model_validate(x) for x in state.get("doc_fields", [])],
            record_check=m("record_check", RecordCheck), hospital=m("hospital", HospitalCheck),
            referral=m("referral", ReferralCheck), docs_check=m("docs_check", DocCompleteness), clock=m("clock", ClockResult),
        )
