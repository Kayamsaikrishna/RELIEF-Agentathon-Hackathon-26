"""Pre-authorisation clock. Pure date arithmetic; no model.

Sources disagree on the limit (HBP 2.2 says 6 hours; the CAG audit refers to a specified period of
12 hours), so each limit is reported separately with its rule id.
"""
from __future__ import annotations

from datetime import datetime, timezone

from relief.contracts.schemas import CaseInput, ClockResult, LimitCheck

LIMITS: list[tuple[str, float]] = [("HBP-PREAUTH-6H", 6.0), ("CAG-PREAUTH-12H", 12.0)]


def preauth_clock(case: CaseInput, now: datetime | None = None) -> ClockResult:
    if case.preauth_submitted_at is None:
        return ClockResult(explanation="No pre-authorisation submission time was provided.")
    ref = case.preauth_decision_at or case.as_of or now or datetime.now(timezone.utc)
    if ref.tzinfo is None:
        ref = ref.replace(tzinfo=timezone.utc)
    hours = (ref - case.preauth_submitted_at).total_seconds() / 3600.0
    if hours < 0:
        return ClockResult(explanation="The decision or reference time is before the submission time; check the times entered.")
    limits = [LimitCheck(rule_id=rid, limit_hours=lim, exceeded="yes" if hours > lim else "no") for rid, lim in LIMITS]
    decided = case.preauth_decision_at is not None
    state = "took" if decided else "has been pending for"
    parts = [f"Pre-authorisation {state} {hours:.1f} hours."]
    for lc in limits:
        if lc.exceeded == "yes":
            parts.append(f"This is beyond the {lc.limit_hours:g}-hour period in {lc.rule_id}.")
    return ClockResult(hours_elapsed=round(hours, 2), decision_recorded=decided, limits=limits, explanation=" ".join(parts))
