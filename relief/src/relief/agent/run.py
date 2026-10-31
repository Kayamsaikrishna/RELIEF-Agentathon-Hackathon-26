"""Command line: python -m relief.agent.run case.json [--approve|--reject] [--no-llm]"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile

from relief.agent.service import Agent
from relief.config import get_settings
from relief.contracts.schemas import CaseInput, Decision
from relief.llm.client import OllamaClient


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="relief.agent.run")
    ap.add_argument("case_file")
    ap.add_argument("--no-llm", action="store_true", help="use the rule-based fallbacks only")
    ap.add_argument("--approve", action="store_true")
    ap.add_argument("--reject", action="store_true")
    ap.add_argument("--keep", action="store_true", help="keep checkpoints in RELIEF_VAR_DIR instead of a temp file")
    a = ap.parse_args(argv)
    settings = get_settings()
    case = CaseInput.model_validate(json.load(open(a.case_file, encoding="utf-8")))
    llm = None if a.no_llm else OllamaClient(settings)
    if llm is not None and not llm.health()[0]:
        print("Model not reachable; continuing with rule-based fallbacks.", file=sys.stderr)
    ck = None if a.keep else tempfile.mktemp(suffix=".sqlite")
    agent = Agent(settings, llm=llm, checkpoint_path=ck)
    res = agent.run_case(case)
    if res.status.value == "awaiting_approval" and (a.approve or a.reject):
        res = agent.resume_case(case.case_id, Decision(action="approve" if a.approve else "reject", decided_by="cli"))
    print(res.model_dump_json(indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
