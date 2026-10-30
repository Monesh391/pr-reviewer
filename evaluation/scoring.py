"""Turn raw review results into the numbers you put on your resume."""

TOLERANCE = 2  # a finding within 2 lines of a known bug counts as a hit


def _ratio(a: float, b: float):
    return round(a / b, 3) if b else None


def score(results: list) -> dict:
    """results: [{bug_lines: [int], findings: [{line: int}], cost_usd, latency_s}]"""
    total_bugs = found_bugs = total_findings = matched = 0
    clean_cases = clean_flagged = 0
    for r in results:
        bugs = r["bug_lines"]
        lines = [f["line"] for f in r["findings"]]
        total_bugs += len(bugs)
        total_findings += len(lines)
        found_bugs += sum(1 for b in bugs if any(abs(b - l) <= TOLERANCE for l in lines))
        matched += sum(1 for l in lines if any(abs(b - l) <= TOLERANCE for b in bugs))
        if not bugs:
            clean_cases += 1
            clean_flagged += 1 if lines else 0
    n = len(results)
    return {
        "cases": n,
        "bugs_total": total_bugs,
        "bugs_found": found_bugs,
        "recall": _ratio(found_bugs, total_bugs),
        "findings_total": total_findings,
        "precision": _ratio(matched, total_findings),
        "clean_cases_flagged": f"{clean_flagged}/{clean_cases}",
        "false_alarm_rate_on_clean": _ratio(clean_flagged, clean_cases),
        "avg_cost_usd": round(sum(r["cost_usd"] for r in results) / n, 5) if n else None,
        "avg_latency_s": round(sum(r["latency_s"] for r in results) / n, 2) if n else None,
    }
