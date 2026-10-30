"""FastAPI server: receives GitHub webhooks and triggers reviews."""
import hashlib
import hmac
import logging
import os

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

import config  # noqa: F401  (loads .env)
from pipeline import handle_pull_request

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("pr-reviewer")

WEBHOOK_SECRET = os.environ["GITHUB_WEBHOOK_SECRET"]
HANDLED_ACTIONS = {"opened", "reopened", "synchronize", "ready_for_review"}

app = FastAPI(title="AI PR Reviewer")


def verify_signature(body: bytes, signature: str | None) -> bool:
    """Make sure the request really came from GitHub."""
    if not signature:
        return False
    expected = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


async def _safe_handle(payload: dict) -> None:
    try:
        await handle_pull_request(payload)
    except Exception:  # never crash the server because one review failed
        log.exception("Review failed")


@app.get("/")
def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: str = Header(None),
):
    body = await request.body()
    if not verify_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    if x_github_event == "pull_request" and payload.get("action") in HANDLED_ACTIONS:
        # GitHub expects a reply within 10s, so review in the background.
        background_tasks.add_task(_safe_handle, payload)
    return {"ok": True}
