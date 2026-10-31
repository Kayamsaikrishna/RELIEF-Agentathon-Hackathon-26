# Evaluation

30 synthetic cases (`src/relief/eval/cases.py`): 4 each of six blockers (referral, entitlement, linkage, improper charge, empanelment, forms), 3 escalation-only, 3 insufficient-evidence. 10 dev / 20 test. Each case changes one thing in a clean file, so the answer key follows from the cited rule, not from the agent. Hospital reasons are plain, vague or misleading (one third each), as real reasons often are.

Baseline: a keyword matcher on the hospital's stated reason.

Results (rule-based path, no model): see `EVALUATION_RESULTS.md`. Agent 30/30 vs baseline 11/30.

**Read this carefully:** the cases were written by the same team that wrote the rules in code, so 30/30 shows the code and the rules agree; it is not an accuracy estimate for real cases. The baseline gap shows that the stated reason alone is a poor guide. Real validation needs de-identified cases labelled by facilitators. The `--llm` run measures what the model changes (ordering, ranking, summary wording) and has not been run.
