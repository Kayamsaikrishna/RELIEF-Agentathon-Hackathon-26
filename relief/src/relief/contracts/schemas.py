"""Shared contracts. Every lane builds against these types.

Rules:
  * "unknown" is a valid answer everywhere. No tool may guess.
  * Inputs forbid unknown fields so typos fail loudly.
  * Findings never state eligibility or medical conclusions; they say what looks inconsistent.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Tri = Literal["yes", "no", "unknown"]
CASE_ID_PATTERN = r"^[A-Za-z0-9_-]{1,64}$"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


# --------------------------------------------------------------------------------------
# Enumerations
# --------------------------------------------------------------------------------------
class Blocker(str, Enum):
    """The six RELIEF blockers plus two non-diagnoses."""

    REFERRAL = "REFERRAL"
    ENTITLEMENT = "ENTITLEMENT"
    LINKAGE = "LINKAGE"
    IMPROPER_CHARGE = "IMPROPER_CHARGE"
    EMPANELMENT = "EMPANELMENT"
    FORMS = "FORMS"
    ESCALATION_ONLY = "ESCALATION_ONLY"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class DocKind(str, Enum):
    CARD = "card"
    ID_PROOF = "id_proof"
    REFERRAL_LETTER = "referral_letter"
    PREAUTH_FORM = "preauth_form"
    REFUSAL_NOTE = "refusal_note"
    CLINICAL_NOTES = "clinical_notes"
    DIAGNOSTIC_REPORT = "diagnostic_report"
    BILL = "bill"
    DISCHARGE_SUMMARY = "discharge_summary"


class Confidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CaseStatus(str, Enum):
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    HANDOVER = "handover"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    ERROR = "error"


# --------------------------------------------------------------------------------------
# Case input
# --------------------------------------------------------------------------------------
class CardData(Strict):
    name: str = Field(min_length=1, max_length=200)
    card_id: str = Field(min_length=1, max_length=64)
    family_id: Optional[str] = Field(default=None, max_length=64)
    dob: Optional[date] = None
    state: Optional[str] = Field(default=None, max_length=64)
    scheme_name: Optional[str] = Field(default=None, max_length=120)
    id_type: Optional[str] = Field(default=None, max_length=64)


class DocRef(Strict):
    doc_id: str = Field(pattern=CASE_ID_PATTERN)
    kind: DocKind
    path: Optional[str] = Field(default=None, description="Image file path (read with OCR)")
    text: Optional[str] = Field(default=None, max_length=20000, description="Already-typed text of the document")

    @model_validator(mode="after")
    def _one_source(self) -> "DocRef":
        if not self.path and not self.text:
            raise ValueError("a document needs a path or text")
        return self


class ReferralInput(Strict):
    present: Tri = "unknown"
    letter_id: Optional[str] = Field(default=None, max_length=64)
    issued_on: Optional[date] = None


class PaymentRequest(Strict):
    """A request for money made to the patient by the hospital."""

    amount_inr: float = Field(ge=0)
    purpose: str = Field(max_length=300)
    wallet_exhausted: Tri = "unknown"
    disclosed_in_advance: Tri = "unknown"


class CaseInput(Strict):
    case_id: str = Field(pattern=CASE_ID_PATTERN)
    card: CardData
    documents: list[DocRef] = Field(default_factory=list, max_length=20)
    hospital_id: str = Field(min_length=1, max_length=64)
    procedure_code: str = Field(min_length=1, max_length=64)
    refusal_reason: str = Field(min_length=1, max_length=2000, description="Reason the hospital gave, in its own words")
    bis_status: Literal["verified", "not_found", "unknown"] = Field(
        default="unknown",
        description="Result of the facilitator's lookup in the beneficiary identification system, entered by a person",
    )
    referral: ReferralInput = Field(default_factory=ReferralInput)
    payment_request: Optional[PaymentRequest] = None
    admission_date: Optional[date] = None
    preauth_submitted_at: Optional[datetime] = None
    preauth_decision_at: Optional[datetime] = None
    as_of: Optional[datetime] = Field(default=None, description="Reference time; defaults to now")
    notes: str = Field(default="", max_length=2000)
    language: Literal["en"] = "en"
    synthetic: bool = Field(default=False, description="True for generated demo and evaluation cases")

    @field_validator("preauth_submitted_at", "preauth_decision_at", "as_of")
    @classmethod
    def _aware(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v


# --------------------------------------------------------------------------------------
# Tool outputs
# --------------------------------------------------------------------------------------
class DocFields(Strict):
    doc_id: str
    kind: DocKind
    fields: dict[str, str] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    status: Literal["ok", "partial", "unreadable"] = "unreadable"
    note: str = ""


class Mismatch(Strict):
    field: str
    card_value: str
    doc_value: str
    doc_id: str
    kind: Literal["different", "possible_variant"] = "different"
    similarity: Optional[float] = None


class RecordCheck(Strict):
    mismatches: list[Mismatch] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)
    compared_fields: int = 0
    status: Literal["consistent", "mismatch", "unknown"] = "unknown"


class HospitalCheck(Strict):
    found: bool = False
    hospital_name: Optional[str] = None
    hospital_type: Literal["public", "private", "unknown"] = "unknown"
    state: Optional[str] = None
    district: Optional[str] = None
    empanelled: Tri = "unknown"
    package_listed: Tri = "unknown"
    specialty: Optional[str] = None
    procedure_name: Optional[str] = None
    tier: Optional[Literal["2A", "2B", "3A", "4A"]] = None
    reserved_for_public: Tri = "unknown"
    registry_version: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class ReferralCheck(Strict):
    required: Tri = "unknown"
    present: Tri = "unknown"
    expired: Tri = "unknown"
    retrospective: Tri = "unknown"
    days_since_issue: Optional[int] = None
    tier: Optional[str] = None
    rule_ids: list[str] = Field(default_factory=list)
    explanation: str = ""


class LimitCheck(Strict):
    rule_id: str
    limit_hours: float
    exceeded: Tri


class ClockResult(Strict):
    hours_elapsed: Optional[float] = None
    decision_recorded: bool = False
    limits: list[LimitCheck] = Field(default_factory=list)
    explanation: str = ""


class RulePassage(Strict):
    rule_id: str
    source_id: str
    source_title: str
    issuer: str
    date: str
    url: str
    section: str
    page: Optional[str] = None
    quote: str
    text: str
    quote_checked: bool = False
    score: Optional[float] = None


class DocCompleteness(Strict):
    required: list[DocKind] = Field(default_factory=list)
    provided: list[DocKind] = Field(default_factory=list)
    missing: list[DocKind] = Field(default_factory=list)
    status: Literal["complete", "incomplete", "unknown"] = "unknown"


# --------------------------------------------------------------------------------------
# Agent state and outputs
# --------------------------------------------------------------------------------------
class Evidence(Strict):
    evidence_id: str
    tool: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    rule_ids: list[str] = Field(default_factory=list)


class BlockerFinding(Strict):
    blocker: Blocker
    confidence: Confidence
    evidence_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    wording: str = Field(description="Starts with 'Possible'; says what is inconsistent and what to verify")
    source: Literal["rules", "model"] = "rules"


class ChecklistItem(Strict):
    key: Optional[str] = Field(default=None, description="Stable id of the step, used by the verifier")
    text: str
    required: bool = True
    rule_id: Optional[str] = None


class Action(Strict):
    kind: Literal["submit_preauth", "send_escalation", "remind"]
    payload: dict[str, Any] = Field(default_factory=dict)


class Plan(Strict):
    checklist: list[ChecklistItem] = Field(default_factory=list)
    alt_hospitals: list[str] = Field(default_factory=list)
    letter_text: Optional[str] = None
    drafts: dict[str, str] = Field(default_factory=dict, description="Draft texts by name: checklist, hospital_list, escalation")
    actions: list[Action] = Field(default_factory=list)
    summary: str = ""


class Verification(Strict):
    citations_ok: bool = False
    fields_ok: bool = False
    safety_ok: bool = False
    forbidden_phrases: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    attempts: int = 0

    @property
    def passed(self) -> bool:
        return self.citations_ok and self.fields_ok and self.safety_ok


class TraceEvent(Strict):
    ts: datetime = Field(default_factory=utcnow)
    node: str
    tool: Optional[str] = None
    kind: Literal["tool", "model", "code", "gate", "fallback", "safety", "error"] = "code"
    input_summary: str = ""
    output_summary: str = ""


class Decision(Strict):
    action: Literal["approve", "edit", "reject"]
    edited_plan: Optional[Plan] = None
    note: str = Field(default="", max_length=1000)
    decided_by: str = Field(default="facilitator", max_length=100)
    ts: datetime = Field(default_factory=utcnow)

    @model_validator(mode="after")
    def _edit_needs_plan(self) -> "Decision":
        if self.action == "edit" and self.edited_plan is None:
            raise ValueError("an edit decision needs edited_plan")
        return self


class CaseResult(Strict):
    case_id: str
    status: CaseStatus = CaseStatus.RUNNING
    findings: list[BlockerFinding] = Field(default_factory=list)
    plan: Optional[Plan] = None
    verification: Optional[Verification] = None
    handover_missing: list[str] = Field(default_factory=list)
    handover_reason: str = ""
    emergency_notice: Optional[str] = None
    evidence: list[Evidence] = Field(default_factory=list)
    rules_cited: list[RulePassage] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)
    decisions: list[Decision] = Field(default_factory=list)
    llm_used: bool = False
    model: Optional[str] = None
    synthetic: bool = False
    error: Optional[str] = None

    @property
    def main_blocker(self) -> Optional[Blocker]:
        return self.findings[0].blocker if self.findings else None
