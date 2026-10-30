"""Small helper for talking to the GitHub API as a GitHub App."""
import os
import time

import httpx
import jwt

API = "https://api.github.com"


def _private_key() -> str:
    inline = os.environ.get("GITHUB_PRIVATE_KEY")
    if inline:
        return inline.replace("\\n", "\n")
    with open(os.environ["GITHUB_PRIVATE_KEY_PATH"], "r") as f:
        return f.read()


def _app_jwt() -> str:
    """Short-lived JWT that proves we are the GitHub App."""
    now = int(time.time())
    payload = {"iat": now - 60, "exp": now + 540, "iss": os.environ["GITHUB_APP_ID"]}
    return jwt.encode(payload, _private_key(), algorithm="RS256")


def _headers(token: str, accept: str = "application/vnd.github+json") -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": accept,
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def get_installation_token(installation_id: int) -> str:
    url = f"{API}/app/installations/{installation_id}/access_tokens"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=_headers(_app_jwt()))
        r.raise_for_status()
        return r.json()["token"]


async def get_pr_files(token: str, repo: str, number: int) -> list:
    """Changed files of a PR (each has filename, status, patch)."""
    files = []
    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, 4):  # up to 300 files
            url = f"{API}/repos/{repo}/pulls/{number}/files"
            r = await client.get(
                url, headers=_headers(token), params={"per_page": 100, "page": page}
            )
            r.raise_for_status()
            batch = r.json()
            files.extend(batch)
            if len(batch) < 100:
                break
    return files


async def get_file_content(token: str, repo: str, path: str, ref: str):
    """Raw text of a file at a commit, or None if it can't be fetched."""
    url = f"{API}/repos/{repo}/contents/{path}"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(
            url,
            headers=_headers(token, "application/vnd.github.raw+json"),
            params={"ref": ref},
        )
    return r.text if r.status_code == 200 else None


async def post_pr_comment(token: str, repo: str, pr_number: int, body: str) -> None:
    url = f"{API}/repos/{repo}/issues/{pr_number}/comments"
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=_headers(token), json={"body": body})
        r.raise_for_status()


async def post_review(
    token: str, repo: str, number: int, commit_sha: str, body: str, comments: list
) -> None:
    """Post one review with inline comments attached to specific lines."""
    url = f"{API}/repos/{repo}/pulls/{number}/reviews"
    payload = {"commit_id": commit_sha, "body": body, "event": "COMMENT", "comments": comments}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=_headers(token), json=payload)
        r.raise_for_status()
