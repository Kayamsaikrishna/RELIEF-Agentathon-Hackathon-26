"""Run the 30-case evaluation: agent vs a keyword baseline. python -m relief.eval.run_eval [--llm] [--out report.md]"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from collections import defaultdict

from relief.agent.service import Agent
from relief.config import get_settings
from relief.contracts.schemas import CaseInput
from relief.eval.cases import build
from relief.llm.client import OllamaClient

KEYWORDS = [("ENTITLEMENT", r"card|eligib|record|not valid|portal"), ("REFERRAL", r"referr|district hospital|file is not complete"),
            ("LINKAGE", r"mismatch|match|verification|number"), ("IMPROPER_CHARGE", r"pay|deposit|buy|medicine|fee"),
            ("EMPANELMENT", r"not part|not done|not available|package|scheme for this"), ("FORMS", r"reject|document"),
            ("ESCALATION_ONLY", r"waiting|approval")]


def baseline(reason: str) -> str:
    for b, pat in KEYWORDS:
        if re.search(pat, reason, re.I):
            return b
    return "INSUFFICIENT_EVIDENCE"


def predicted(res) -> str:
    return res.main_blocker.value if res.main_blocker else "NONE"


def run(use_llm: bool) -> dict:
    s = get_settings()
    llm = OllamaClient(s) if use_llm else None
    if use_llm and not llm.health()[0]:
        raise SystemExit("Model not reachable: " + llm.health()[1])
    agent = Agent(s, llm=llm, checkpoint_path=tempfile.mktemp(suffix=".sqlite"))
    rows = []
    for item in build():
        case = CaseInput.model_validate(item["case"])
        res = agent.run_case(case)
        exp = item["expected_blocker"]
        p = predicted(res)
        rows.append({"id": case.case_id, "split": item["split"], "expected": exp, "agent": p, "baseline": baseline(case.refusal_reason),
                     "status": res.status.value, "verified": bool(res.verification and res.verification.passed) or res.status.value == "handover",
                     "confidence": res.findings[0].confidence.value if res.findings else None,
                     "has_citation": bool(res.rules_cited) or res.status.value == "handover",
                     "unsafe": any(__import__("relief.agent.safety", fromlist=["x"]).forbidden_phrases(t) for t in
                                   ([res.plan.summary] + list(res.plan.drafts.values()) if res.plan else []))})
    return {"rows": rows, "llm": use_llm, "model": s.llm_model if use_llm else None}


def acc(rows, key, split=None):
    r = [x for x in rows if split in (None, x["split"])]
    return sum(x[key] == x["expected"] for x in r), len(r)


def report(d: dict) -> str:
    rows = d["rows"]
    L = [f"# RELIEF evaluation ({'with local model ' + str(d['model']) if d['llm'] else 'rule-based path, no model'})", "",
         "Cases are synthetic; answer keys come from the rule passages by construction (see src/relief/eval/cases.py).",
         "The rule-based path implements the same rules, so these scores check consistency, not real-world accuracy.", "",
         "| Set | Agent top-1 | Keyword baseline |", "|---|---|---|"]
    for sp in (None, "dev", "test"):
        a, n = acc(rows, "agent", sp)
        b, _ = acc(rows, "baseline", sp)
        L.append(f"| {sp or 'all'} ({n}) | {a}/{n} | {b}/{n} |")
    per = defaultdict(lambda: [0, 0])
    for r in rows:
        per[r["expected"]][1] += 1
        per[r["expected"]][0] += r["agent"] == r["expected"]
    L += ["", "| Blocker | Agent correct |", "|---|---|"] + [f"| {k} | {v[0]}/{v[1]} |" for k, v in per.items()]
    L += ["", f"Plans that passed the automatic checks (or were handed over): {sum(r['verified'] for r in rows)}/{len(rows)}",
          f"Cases with a cited rule (or a hand-over): {sum(r['has_citation'] for r in rows)}/{len(rows)}",
          f"Plans containing forbidden wording: {sum(r['unsafe'] for r in rows)}"]
    wrong = [r for r in rows if r["agent"] != r["expected"]]
    if wrong:
        L += ["", "## Misses", ""] + [f"- {r['id']}: expected {r['expected']}, got {r['agent']}" for r in wrong]
    return "\n".join(L) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", action="store_true")
    ap.add_argument("--out", default="docs/EVALUATION_RESULTS.md")
    a = ap.parse_args()
    d = run(a.llm)
    text = report(d)
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    open(a.out, "w", encoding="utf-8").write(text)
    json.dump(d, open(a.out.replace(".md", ".json"), "w"), indent=1)
    print(text)


if __name__ == "__main__":
    main()
