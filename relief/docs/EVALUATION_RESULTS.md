# RELIEF evaluation (rule-based path, no model)

Cases are synthetic; answer keys come from the rule passages by construction (see src/relief/eval/cases.py).
The rule-based path implements the same rules, so these scores check consistency, not real-world accuracy.

| Set | Agent top-1 | Keyword baseline |
|---|---|---|
| all (30) | 30/30 | 11/30 |
| dev (10) | 10/10 | 2/10 |
| test (20) | 20/20 | 9/20 |

| Blocker | Agent correct |
|---|---|
| REFERRAL | 4/4 |
| ENTITLEMENT | 4/4 |
| LINKAGE | 4/4 |
| IMPROPER_CHARGE | 4/4 |
| EMPANELMENT | 4/4 |
| FORMS | 4/4 |
| ESCALATION_ONLY | 3/3 |
| INSUFFICIENT_EVIDENCE | 3/3 |

Plans that passed the automatic checks (or were handed over): 30/30
Cases with a cited rule (or a hand-over): 30/30
Plans containing forbidden wording: 0
