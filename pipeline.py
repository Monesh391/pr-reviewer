"""End-to-end flow for one pull request event."""
import json
import logging
import time

import httpx

import config
from github_client import (
    get_file_content, get_installation_token, get_pr_files, post_pr_comment, post_review,
)
from reviewer import review_files

log = logging.getLogger("pr-reviewer")
ICON = {"high": "🔴", "medium": "🟠", "low": "🟡"}


def format_comment(f) -> str:
    text = f"{ICON.get(f.severity, '')} **{f.severity.title()}**: {f.message}"
    if f.suggestion:
        text += f"\n\n💡 {f.suggestion}"
    return text


def build_summary(result) -> str:
    if result.findings:
        head = f"Found **{len(result.findings)}** potential issue(s)."
    else:
        head = "✅ No issues found in the changed lines."
    stats = (
        f"{result.input_tokens + result.output_tokens} tokens · "
        f"${result.cost_usd:.4f} · {result.latency_s:.1f}s"
    )
    return f"### 🤖 AI Review\n{result.summary}\n\n{head}\n\n<sub>{stats}</sub>"


async def fetch_conventions(token: str, repo: str, ref: str) -> str:
    """Use the repo's own rules: .pr-reviewer.md first, then CONTRIBUTING.md."""
    for name in (".pr-reviewer.md", "CONTRIBUTING.md"):
        text = await get_file_content(token, repo, name, ref)
        if text:
            return text[:3000]
    return ""


def log_review(repo: str, number: int, result) -> None:
    """Append one line of stats per review (used for your resume numbers)."""
    row = {
        "ts": time.time(), "repo": repo, "pr": number,
        "findings": len(result.findings),
        "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
        "cost_usd": round(result.cost_usd, 5), "latency_s": round(result.latency_s, 2),
    }
    with open("reviews.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


async def publish(token, repo, number, sha, result) -> None:
    comments = [
        {"path": f.path, "line": f.line, "side": "RIGHT", "body": format_comment(f)}
        for f in result.findings
    ]
    try:
        await post_review(token, repo, number, sha, build_summary(result), comments)
    except httpx.HTTPStatusError as err:
        if err.response.status_code != 422:
            raise
        # Inline placement failed: fall back to one normal comment.
        bullets = "\n".join(f"- `{f.path}:{f.line}` {f.message}" for f in result.findings)
        await post_pr_comment(token, repo, number, build_summary(result) + "\n\n" + bullets)


async def handle_pull_request(payload: dict) -> None:
    pr = payload["pull_request"]
    if pr.get("draft"):
        return
    repo = payload["repository"]["full_name"]
    number = pr["number"]
    sha = pr["head"]["sha"]
    log.info("Reviewing %s#%s", repo, number)

    token = await get_installation_token(payload["installation"]["id"])
    files = await get_pr_files(token, repo, number)
    conventions = await fetch_conventions(token, repo, sha)

    contents = {}
    for f in files[: config.MAX_FILES]:
        if f["filename"].endswith(".py") and f.get("status") != "removed":
            source = await get_file_content(token, repo, f["filename"], sha)
            if source:
                contents[f["filename"]] = source

    result = await review_files(files, conventions, contents)
    if not result.input_tokens and not result.findings:
        return  # nothing reviewable
    await publish(token, repo, number, sha, result)
    log_review(repo, number, result)
    log.info("Posted %d finding(s) on %s#%s", len(result.findings), repo, number)
