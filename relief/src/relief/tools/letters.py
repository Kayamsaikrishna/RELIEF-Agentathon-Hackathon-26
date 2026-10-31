"""Letters from fixed templates. The model may supply one short summary sentence; everything else is
filled from the case record and the rule base."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_env = Environment(loader=FileSystemLoader(str(Path(__file__).parent / "templates")),
                   undefined=StrictUndefined, autoescape=False, trim_blocks=True, lstrip_blocks=True)
KINDS = {"checklist": "checklist.j2", "escalation": "escalation.j2", "hospital_list": "hospital_list.j2"}
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean(v: Any) -> Any:
    if isinstance(v, str):
        return _CTRL.sub("", v).strip()
    if isinstance(v, list):
        return [_clean(x) for x in v]
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items()}
    return v


def format_draft(text: str) -> str:
    """Format and normalize draft text to prevent unstructured/run-on blocks."""
    if not text:
        return ""
    # 1. Break before checklist checkboxes [ ] if they are preceded by non-newline
    text = re.sub(r'([^\n])\s*(\[[ xX]\])', r'\1\n\n\2', text)

    # 2. Break before section headers
    headers = [
        r"PATIENT & ADMISSION DETAILS:",
        r"INCONSISTENCIES TO BE VERIFIED:",
        r"ACTION SUMMARY:",
        r"STATUTORY BASIS IN PUBLISHED RULES:",
        r"REQUEST:",
        r"What appears inconsistent \(to be verified\):",
        r"Summary:",
        r"Basis in published rules:",
        r"Request:",
        r"Ranking:",
        r"Note:",
    ]
    for h in headers:
        text = re.sub(rf'([^\n])\s*({h})', r'\1\n\n\2', text)

    # 3. Break before bullet points in escalation / inconsistencies if concatenated
    text = re.sub(r'([^\n])\s*(-\s+[A-Z0-9_\-]+:)', r'\1\n\2', text)

    # 4. Break before disclaimer footers
    text = re.sub(r'([^\n])\s*(This checklist is prepared by RELIEF)', r'\1\n\n--------------------------------------------------------------------------------\n\2', text)
    text = re.sub(r'([^\n])\s*(Notes for the facilitator before sending)', r'\1\n\n--------------------------------------------------------------------------------\n\2', text)

    # 5. Clean up numbered checklist items if they lost their numbers or spacing
    lines = text.split('\n')
    new_lines: list[str] = []
    item_idx = 1
    in_items = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Items to complete or confirm:"):
            in_items = True
            new_lines.append(line)
            new_lines.append("")
            continue
        if in_items and (stripped.startswith("This checklist") or stripped.startswith("---")):
            in_items = False
            new_lines.append(line)
            continue
        if in_items and stripped.startswith("[ ]"):
            content = stripped[3:].strip()
            if not re.match(r'^\d+\.', content):
                new_lines.append(f"[ ] {item_idx}. {content}")
                new_lines.append("")
                item_idx += 1
            else:
                new_lines.append(stripped)
                new_lines.append("")
        else:
            new_lines.append(line)

    res = '\n'.join(new_lines)
    res = re.sub(r'\n{3,}', '\n\n', res)
    return res.strip() + "\n"


def render_letter(kind: str, facts: dict[str, Any]) -> str:
    if kind not in KINDS:
        raise ValueError(f"unknown letter kind {kind!r}")
    raw = _env.get_template(KINDS[kind]).render(**_clean(facts)).strip()
    return format_draft(raw)
