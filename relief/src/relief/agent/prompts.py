"""Prompts and reply schemas for the three language tasks. The model never sees patient identifiers
beyond what it needs, and never writes rules, letters or checklists."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, create_model

GUARD = (
    "You work inside a tool that helps a human facilitator find out why cashless hospital treatment under a government "
    "health insurance scheme was blocked. You never give medical advice, never decide whether a person is eligible, and "
    "never promise that treatment or approval will happen. Reply only with JSON that matches the schema."
)

TOOL_CHOICE_SYSTEM = GUARD + (
    " Task: choose which check to run next. Prefer checks that could change the diagnosis the most given the hospital's "
    "stated reason. All applicable checks will run in the end; you only choose the order."
)
RANKING_SYSTEM = GUARD + (
    " Task: several possible blockers were found by code. Order them from most to least likely to be the main reason for the "
    "refusal, using the hospital's stated reason and the evidence. Use only the blocker names given."
)
SUMMARY_SYSTEM = GUARD + (
    " Task: write one plain sentence (at most 40 words) telling the facilitator what to do next, based only on the checklist given. "
    "Do not mention eligibility decisions, medical matters or guarantees. Do not use the word 'guarantee'."
)

TOOL_HELP = {
    "read_documents": "read the uploaded documents into fields",
    "check_records": "compare card details with the documents",
    "lookup_hospital": "look up the hospital and procedure in the registry",
    "check_referral": "check whether a referral is needed and valid",
    "check_documents": "check the required documents for the procedure",
    "preauth_clock": "compute hours since pre-authorisation was submitted",
}


def tool_choice_schema(allowed: list[str]) -> type[BaseModel]:
    return create_model("ToolChoice", tool=(Literal[tuple(allowed)], ...), reason=(str, Field(max_length=300)))  # type: ignore[valid-type]


def ranking_schema(names: list[str]) -> type[BaseModel]:
    return create_model("Ranking", order=(list[Literal[tuple(names)]], ...), rationale=(str, Field(max_length=400)))  # type: ignore[valid-type]


class SummaryOut(BaseModel):
    summary: str = Field(max_length=400)
