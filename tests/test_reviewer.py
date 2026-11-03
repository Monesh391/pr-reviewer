import asyncio

import reviewer
from models import Finding
from reviewer import filter_findings, merge_findings, parse_llm_json, review_files


def item(**kw):
    base = {"path": "a.py", "line": 2, "severity": "high", "confidence": 0.9, "message": "bad"}
    base.update(kw)
    return base


def test_parse_llm_json_handles_fences_and_garbage():
    fenced = '```json\n{"summary": "ok", "findings": []}\n```'
    assert parse_llm_json(fenced)["summary"] == "ok"
    assert parse_llm_json("no json here") == {"summary": "", "findings": []}
    assert parse_llm_json("{broken") == {"summary": "", "findings": []}


def test_filter_drops_bad_findings():
    valid = {"a.py": {1, 2, 3}}
    raw = [
        item(),
        item(line=99),                 # line not in the diff
        item(path="b.py"),             # unknown file
        item(confidence=0.3),          # too weak
        item(line="x"),                # not a number
        item(message="  "),            # empty message
    ]
    out = filter_findings(raw, valid, min_conf=0.7, max_n=10)
    assert len(out) == 1 and out[0].line == 2


def test_filter_sorts_dedupes_and_caps():
    valid = {"a.py": set(range(1, 20))}
    raw = [item(line=i, severity="low") for i in range(1, 11)]
    raw.append(item(line=15, severity="high", message="worse"))
    raw.append(item(line=15, severity="high", message="worse"))  # duplicate
    out = filter_findings(raw, valid, min_conf=0.7, max_n=3)
    assert len(out) == 3 and out[0].severity == "high"


def test_merge_prefers_linter_on_same_line():
    llm = [Finding("a.py", 2, "high", 0.9, "llm says")]
    lint = [Finding("a.py", 2, "medium", 1.0, "ruff says", source="ruff")]
    merged = merge_findings(llm, lint, max_n=5)
    assert len(merged) == 1 and merged[0].source == "ruff"


def test_review_files_end_to_end_with_fake_llm(monkeypatch):
    async def fake_llm(system, user):
        assert "L2|" in user  # numbered diff reached the prompt
        reply = ('{"summary": "One bug.", "findings": [{"path": "a.py", "line": 2, '
                 '"severity": "high", "confidence": 0.95, "message": "crash", "suggestion": "fix"}]}')
        return reply, 1000, 200

    monkeypatch.setattr(reviewer, "call_llm", fake_llm)
    files = [{"filename": "a.py", "status": "added", "patch": "@@ -0,0 +1,3 @@\n+a = 1\n+b = 1 / 0\n+c = 2"}]
    result = asyncio.run(review_files(files))
    assert result.summary == "One bug."
    assert [f.line for f in result.findings] == [2]
    assert result.input_tokens == 1000
    assert result.cost_usd >= 0


def test_review_files_skips_unreviewable(monkeypatch):
    files = [{"filename": "package-lock.json", "status": "modified", "patch": "@@ -1 +1 @@\n+x"}]
    result = asyncio.run(review_files(files))
    assert result.findings == [] and result.input_tokens == 0
