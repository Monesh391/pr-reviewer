"""Measure the reviewer.

  python -m evaluation.run_eval          # synthetic cases with known bugs
  python -m evaluation.run_eval --real   # real PRs from collect_prs.py -> CSV to label
"""
import asyncio
import csv
import json
import sys
from pathlib import Path

from evaluation.cases import build_cases
from evaluation.scoring import score
from reviewer import review_files

HERE = Path(__file__).parent


async def run_synthetic() -> None:
    results = []
    for case in build_cases():
        files = [{"filename": case["filename"], "status": "added", "patch": case["patch"]}]
        res = await review_files(files, "", {case["filename"]: case["code"]})
        results.append({
            "id": case["id"],
            "bug_lines": case["bug_lines"],
            "findings": [{"line": f.line, "message": f.message} for f in res.findings],
            "cost_usd": res.cost_usd,
            "latency_s": res.latency_s,
        })
        print(f"{case['id']:<22} bugs={case['bug_lines']} "
              f"found={[f.line for f in res.findings]}")
    summary = score(results)
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2))
    (HERE / "eval_results.json").write_text(
        json.dumps({"summary": summary, "cases": results}, indent=2), encoding="utf-8"
    )


async def run_real() -> None:
    prs = json.loads((HERE / "real_prs.json").read_text(encoding="utf-8"))
    rows = []
    for pr in prs:
        res = await review_files(pr["files"], "", {})
        for f in res.findings:
            rows.append([pr["repo"], pr["number"], f.path, f.line, f.severity,
                         f.message, ""])  # last column: you fill in tp / fp
        print(f"{pr['repo']}#{pr['number']}: {len(res.findings)} finding(s)")
    out = HERE / "real_pr_findings.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["repo", "pr", "path", "line", "severity", "message", "verdict"])
        w.writerows(rows)
    print(f"\nWrote {out}. Open it, mark each row tp (real issue) or fp (false alarm),"
          " then run: python -m evaluation.summarize_labels")


if __name__ == "__main__":
    asyncio.run(run_real() if "--real" in sys.argv else run_synthetic())
