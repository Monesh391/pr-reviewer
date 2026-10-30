from evaluation.cases import build_cases
from evaluation.scoring import score


def test_score_basic():
    results = [
        {"bug_lines": [5], "findings": [{"line": 6}], "cost_usd": 0.01, "latency_s": 2.0},
        {"bug_lines": [], "findings": [{"line": 3}], "cost_usd": 0.01, "latency_s": 2.0},
        {"bug_lines": [], "findings": [], "cost_usd": 0.01, "latency_s": 2.0},
    ]
    s = score(results)
    assert s["recall"] == 1.0
    assert s["precision"] == 0.5
    assert s["false_alarm_rate_on_clean"] == 0.5


def test_cases_have_answer_keys():
    cases = build_cases()
    assert len(cases) >= 10
    assert any(c["bug_lines"] for c in cases) and any(not c["bug_lines"] for c in cases)
    for c in cases:
        assert "# BUG" not in c["code"] and "# BUG" not in c["patch"]
