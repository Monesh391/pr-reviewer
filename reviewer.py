
"""The AI brain: build the prompt, call the LLM, validate and filter findings."""

import asyncio
import json
import os
# AI PR Reviewer test deployment
import time

import config
from dotenv import load_dotenv
from diff_utils import (
    added_lines,
    limit_files,
    number_patch,
    should_review,
    valid_lines,
)
from linter import lint_python
from models import Finding, ReviewResult

load_dotenv()

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


SYSTEM_PROMPT = """You are a senior software engineer performing a careful pull request review.

Your goal is to identify genuine bugs and security vulnerabilities without producing false alarms.

Check for these categories:

1. LOGIC AND BOUNDARY ERRORS
- Off-by-one errors involving range(), indexes, slices, and loop boundaries.
- Incorrect <, <=, >, and >= comparisons.
- Missing first or last elements during iteration.
- Empty lists, empty strings, and boundary input values.
- Incorrect conditions and unreachable code.

2. SECURITY VULNERABILITIES
- SQL injection caused by concatenating untrusted input into SQL queries.
- Path traversal caused by user-controlled paths, including ../ sequences,
  absolute paths, and paths that escape an intended directory.
- Hardcoded credentials, API keys, passwords, and secrets.
- Missing authorization checks and unsafe handling of untrusted input.

3. RUNTIME AND DATA ERRORS
- Division or modulo by zero.
- None/null dereferences and invalid type assumptions.
- Mutable default arguments that can leak state between function calls.
- Exceptions that are silently swallowed when they hide real failures.
- Incorrect resource handling and missing required cleanup.

REVIEWING RULES:
- Analyze the actual code and its context. Do not report a bug merely because
  a pattern looks suspicious.
- For loops and indexes, mentally test empty, single-element, and
  multi-element inputs where relevant.
- For file paths, determine whether untrusted input can escape the intended
  base directory. Do not report path traversal when the code safely prevents it.
- For SQL, distinguish unsafe string interpolation from parameterized queries.
- Do not assume every exception handler or mutable default is necessarily
  a bug without considering its behavior.
- Prefer concrete, reproducible problems over speculative concerns.
- Do not report formatting issues, personal preferences, or code that is
  merely capable of being improved.
- Do not repeat issues already reported by static analysis.
- Only report issues on changed lines carrying a line-number prefix such as
  L12|+code. Use that exact new-file line number in the finding.
- If a bug is on an unchanged line, report it only if the relevant changed
  line itself introduces or directly causes the problem.
- If the code is correct, return an empty findings array.

SEVERITY:
- high: serious security exposure, data loss, or major failure.
- medium: meaningful functional bug or exploitable weakness with limited scope.
- low: minor but concrete correctness issue.

Return ONLY valid JSON in exactly this shape:
{
  "summary": "<1-2 sentence overview>",
  "findings": [
    {
      "path": "<file>",
      "line": 12,
      "severity": "high|medium|low",
      "confidence": 0.95,
      "message": "<specific problem and why it occurs>",
      "suggestion": "<short actionable fix, or empty string>"
    }
  ]
}"""



def build_prompt(files: list, conventions: str, lint_findings: list) -> str:
    parts = []

    if conventions:
        parts.append(f"## Repository conventions\n{conventions}\n")

    if lint_findings:
        known = "\n".join(
            f"- {f.path}:{f.line} {f.message}"
            for f in lint_findings
        )
        parts.append(
            "## Already reported by static analysis (do not repeat)\n"
            f"{known}\n"
        )

    parts.append("## Pull request diff")

    for file in files:
        parts.append(
            f"\n### File: {file['filename']}\n"
            f"{number_patch(file['patch'])}"
        )

    return "\n".join(parts)


async def call_llm(system: str, user: str):
    """Call the Google Gemini API.

    Returns (text, input_tokens, output_tokens).
    """
    import httpx

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. "
            "Check that your .env file is in the project root."
        )

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json",
    }

    body = {
        "systemInstruction": {
            "parts": [{"text": system}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": user}]
            }
        ],
        "generationConfig": {
            "maxOutputTokens": 2000,
            "responseMimeType": "application/json",
        },
    }

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{model}:generateContent"
    )

    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            url,
            headers=headers,
            json=body,
        )
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])

    if not candidates:
        raise RuntimeError(
            "Gemini returned no response: "
            f"{data.get('promptFeedback', {})}"
        )

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(
        part.get("text", "")
        for part in parts
    )

    usage = data.get("usageMetadata", {})

    return (
        text,
        usage.get("promptTokenCount", 0),
        usage.get("candidatesTokenCount", 0),
    )


def parse_llm_json(text: str) -> dict:
    """Extract the JSON object from the model reply."""
    empty = {"summary": "", "findings": []}

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end <= start:
        return empty

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return empty

    return data if isinstance(data, dict) else empty


def filter_findings(
    raw: list,
    valid: dict,
    min_conf: float,
    max_n: int,
) -> list:
    """Drop invalid, weak, duplicate findings and cap the count."""
    out = []
    seen = set()

    for item in raw if isinstance(raw, list) else []:
        try:
            path = str(item["path"])
            line = int(item["line"])
            confidence = float(item.get("confidence", 0))
            message = str(item["message"]).strip()
        except (KeyError, TypeError, ValueError):
            continue

        severity = str(item.get("severity", "low")).lower()

        if severity not in SEVERITY_ORDER:
            severity = "low"

        if (
            not message
            or confidence < min_conf
            or line not in valid.get(path, set())
        ):
            continue

        key = (path, line, message[:40])

        if key in seen:
            continue

        seen.add(key)

        out.append(
            Finding(
                path,
                line,
                severity,
                confidence,
                message,
                str(item.get("suggestion", "")).strip(),
            )
        )

    out.sort(
        key=lambda finding: (
            SEVERITY_ORDER[finding.severity],
            -finding.confidence,
        )
    )

    return out[:max_n]


def merge_findings(llm: list, lint: list, max_n: int) -> list:
    """Combine LLM and linter findings; lint wins for the same line."""
    by_line = {
        (finding.path, finding.line): finding
        for finding in llm
    }

    by_line.update({
        (finding.path, finding.line): finding
        for finding in lint
    })

    merged = sorted(
        by_line.values(),
        key=lambda finding: (
            SEVERITY_ORDER[finding.severity],
            -finding.confidence,
        ),
    )

    return merged[:max_n]


def estimate_cost(input_tokens: int, output_tokens: int) -> float:
    """Estimate cost using the configured per-million-token prices."""
    return (
        input_tokens / 1e6 * config.PRICE_PER_MTOK_INPUT
        + output_tokens / 1e6 * config.PRICE_PER_MTOK_OUTPUT
    )


async def review_files(
    files: list,
    conventions: str = "",
    contents: dict = None,
) -> ReviewResult:
    """Review changed files.

    files: [{filename, status, patch}]
    contents: {path: source}
    """
    start = time.monotonic()

    reviewable = [
        file
        for file in files
        if (
            file.get("patch")
            and file.get("status") != "removed"
            and should_review(file["filename"])
        )
    ]

    included, skipped = limit_files(
        reviewable,
        config.MAX_DIFF_CHARS,
        config.MAX_FILES,
    )

    if not included:
        return ReviewResult(
            summary="No reviewable code changes.",
            skipped_files=skipped,
        )

    valid = {
        file["filename"]: valid_lines(file["patch"])
        for file in included
    }

    added = {
        file["filename"]: added_lines(file["patch"])
        for file in included
    }

    lint_findings = []

    py_sources = {
        path: source
        for path, source in (contents or {}).items()
        if path in added and path.endswith(".py")
    }

    if py_sources:
        lint_findings = await asyncio.to_thread(
            lint_python,
            py_sources,
            {path: added[path] for path in py_sources},
        )

    text, tokens_in, tokens_out = await call_llm(
        SYSTEM_PROMPT,
        build_prompt(included, conventions, lint_findings),
    )

    data = parse_llm_json(text)

    llm_findings = filter_findings(
        data.get("findings", []),
        valid,
        config.MIN_CONFIDENCE,
        config.MAX_COMMENTS,
    )

    findings = merge_findings(
        llm_findings,
        lint_findings,
        config.MAX_COMMENTS,
    )

    return ReviewResult(
        summary=str(data.get("summary", "")).strip(),
        findings=findings,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        latency_s=time.monotonic() - start,
        cost_usd=estimate_cost(tokens_in, tokens_out),
        skipped_files=skipped,
    )
# Testing automatic AI PR review
# Testing GitHub webhook synchronize event
# Testing GitHub webhook synchronization event
# Testing webhook payload logging