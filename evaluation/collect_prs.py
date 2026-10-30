"""Download merged PRs from a public repo for evaluation.

  python -m evaluation.collect_prs owner/repo 10
Set GITHUB_TOKEN to avoid the low anonymous rate limit.
"""
import json
import os
import sys
from pathlib import Path

import httpx

OUT = Path(__file__).parent / "real_prs.json"


def main(repo: str, count: int) -> None:
    headers = {"Accept": "application/vnd.github+json"}
    if os.getenv("GITHUB_TOKEN"):
        headers["Authorization"] = f"Bearer {os.environ['GITHUB_TOKEN']}"
    base = f"https://api.github.com/repos/{repo}"
    existing = json.loads(OUT.read_text()) if OUT.exists() else []
    with httpx.Client(headers=headers, timeout=30) as client:
        prs = client.get(f"{base}/pulls", params={"state": "closed", "per_page": 100}).json()
        added = 0
        for pr in prs:
            if added >= count:
                break
            if not pr.get("merged_at"):
                continue
            files = client.get(f"{base}/pulls/{pr['number']}/files", params={"per_page": 100}).json()
            existing.append({
                "repo": repo, "number": pr["number"], "title": pr["title"],
                "files": [{"filename": f["filename"], "status": f["status"], "patch": f.get("patch", "")}
                          for f in files],
            })
            added += 1
    OUT.write_text(json.dumps(existing, indent=1), encoding="utf-8")
    print(f"Saved {added} PRs from {repo}. Total stored: {len(existing)}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 10)
