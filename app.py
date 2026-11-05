
"""FastAPI server: receives GitHub webhooks and triggers PR reviews."""

import hashlib
import hmac
import logging
import os

from fastapi import (
    BackgroundTasks,
    FastAPI,
    Header,
    HTTPException,
    Request,
)

import config  # noqa: F401 - loads environment variables
from pipeline import handle_pull_request

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pr-reviewer")

WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "")

HANDLED_ACTIONS = {
    "opened",
    "reopened",
    "synchronize",
    "ready_for_review",
}

app = FastAPI(title="AI PR Reviewer")


def verify_signature(body: bytes, signature: str | None) -> bool:
    """Verify that the webhook request came from GitHub."""

    if not WEBHOOK_SECRET or not signature:
        return False

    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)


async def _safe_handle(payload: dict) -> None:
    """Validate the payload and safely start the PR review."""

    try:
        log.info("Starting PR review task")

        installation = payload.get("installation")
        repository = payload.get("repository")
        pull_request = payload.get("pull_request")

        if not isinstance(installation, dict) or not installation.get("id"):
            log.error("Missing installation.id in pull request payload")
            return

        if not isinstance(repository, dict) or not repository.get("full_name"):
            log.error("Missing repository.full_name in payload")
            return

        if not isinstance(pull_request, dict):
            log.error("Missing pull_request object in payload")
            return

        if not pull_request.get("number") or not pull_request.get("head", {}).get("sha"):
            log.error("Missing pull request number or head SHA")
            return

        log.info(
            "Reviewing %s, PR #%s",
            repository["full_name"],
            pull_request["number"],
        )

        await handle_pull_request(payload)

        log.info("PR review task completed successfully")

    except Exception:
        log.exception("Review failed")


@app.get("/")
def health():
    """Health-check endpoint."""
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    """Receive and process GitHub webhook events."""

    body = await request.body()

    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature",
        )

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload",
        )

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=400,
            detail="Webhook payload must be a JSON object",
        )

    action = payload.get("action")

    log.info(
        "Received GitHub event: %s | Action: %s",
        x_github_event,
        action,
    )

    # Ignore ping, push, and other unrelated events.
    if x_github_event != "pull_request":
        return {"ok": True, "message": "Event ignored"}

    if action not in HANDLED_ACTIONS:
        return {"ok": True, "message": "Action ignored"}

    # Only schedule valid pull request events.
    if not isinstance(payload.get("installation"), dict):
        log.error("Pull request event has no installation object")
        return {"ok": True, "message": "Missing installation information"}

    background_tasks.add_task(_safe_handle, payload)

    return {"ok": True, "message": "PR review scheduled"}
