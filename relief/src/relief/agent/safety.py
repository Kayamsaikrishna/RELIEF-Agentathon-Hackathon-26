"""Safety rules enforced in code, never by the model."""
from __future__ import annotations

import re

EMERGENCY_NOTICE = (
    "This case mentions what may be a medical emergency. Please contact emergency services (112) or take the "
    "patient to the nearest hospital emergency department now. RELIEF does not give medical advice and has not "
    "analysed this case."
)

_EMERGENCY = [
    r"chest pain", r"heart attack", r"unconscious", r"unresponsive", r"not breathing", r"stopped breathing",
    r"difficulty (in )?breathing", r"short(ness)? of breath", r"severe bleeding", r"heavy bleeding", r"bleeding (a lot|heavily)",
    r"stroke", r"seizure", r"convulsion", r"overdose", r"poison", r"suicid", r"self[- ]harm", r"collaps(e|ed)",
    r"snake ?bite", r"burns? (all over|severe)", r"head injury",
]
_EMERGENCY_RE = re.compile("|".join(_EMERGENCY), re.I)

# Text RELIEF itself writes must not contain these. (Name, pattern)
_FORBIDDEN: list[tuple[str, str]] = [
    ("eligibility verdict", r"\b(is|are|was|were|isn't|aren't|not)\s+(eligible|ineligible|entitled)\b"),
    ("eligibility verdict", r"\bineligible\b"),
    ("eligibility verdict", r"\byou (are|will be) (eligible|entitled|covered)\b"),
    ("promise of treatment", r"\bguarantee[sd]?\b"),
    ("promise of treatment", r"\bwill (definitely )?be (treated|admitted|approved|covered|cleared)\b"),
    ("promise of treatment", r"\b(is|are) (certain|sure) to\b"),
    ("medical advice", r"\byou should (take|undergo|stop|start|avoid|have)\b"),
    ("medical advice", r"\b(prescribe[sd]?|prescription for)\b"),
    ("medical advice", r"\b\d+\s?(mg|ml|mcg)\b"),
    ("medical advice", r"\b(diagnos(is|ed) (is|of)|you (have|suffer from))\b"),
]
_FORBIDDEN_RE = [(n, re.compile(p, re.I)) for n, p in _FORBIDDEN]


def has_emergency_language(*texts: str) -> bool:
    return any(t and _EMERGENCY_RE.search(t) for t in texts)


def forbidden_phrases(text: str) -> list[str]:
    """Return a label plus the matched text for each forbidden pattern found."""
    hits = []
    for name, rx in _FORBIDDEN_RE:
        for m in rx.finditer(text or ""):
            hits.append(f"{name}: '{m.group(0)}'")
    return hits
