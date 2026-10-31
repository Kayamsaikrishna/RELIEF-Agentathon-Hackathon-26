from relief.eval.cases import build
from relief.eval.run_eval import baseline, run


def test_cases_shape():
    b = build()
    assert len(b) == 30 and sum(x["split"] == "dev" for x in b) == 10
    assert len({x["case"]["case_id"] for x in b}) == 30 and all(x["case"]["synthetic"] for x in b)


def test_rule_based_path_matches_answer_keys(settings):
    rows = run(False)["rows"]
    wrong = [(r["id"], r["expected"], r["agent"]) for r in rows if r["agent"] != r["expected"]]
    assert not wrong, wrong
    assert all(r["verified"] and r["has_citation"] and not r["unsafe"] for r in rows)
    assert sum(baseline(x["case"]["refusal_reason"]) == x["expected_blocker"] for x in build()) < 20
