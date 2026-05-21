"""
Dispatches escalations to the destination configured in AgentContextBase.escalation_destination.
Implemented destinations: webhook. Stubs: email, github_issue, queue.
"""
import hashlib
import hmac
import json
from datetime import datetime, timezone
from typing import Literal

import requests

from src.domain.agent import AgentContextBase
from src.domain.conversation import HistoryMessage, SessionMeta


def dispatch_escalation(
    agent_id: str,
    session_id: str,
    reason: Literal["automatic", "manual"],
    context: AgentContextBase,
    meta: SessionMeta,
    history: list[HistoryMessage],
) -> None:
    dest = context.escalation_destination
    if not dest or dest.type == "none":
        return

    payload = {
        "event": "escalation",
        "session_id": session_id,
        "agent_id": agent_id,
        "user_id": meta.user_id,
        "reason": reason,
        "triggered_at": datetime.now(timezone.utc).isoformat(),
        "last_messages": [{"role": m.role, "content": m.content} for m in history[-5:]],
    }

    if dest.type == "webhook":
        _dispatch_webhook(dest.url, dest.token, payload)


def _sign_payload(body: bytes) -> str | None:
    from src.infrastructure.config import settings
    secret = settings.INTERNAL_TOKEN
    if not secret:
        return None
    sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={sig}"


def _dispatch_webhook(url: str, token: str | None, payload: dict) -> None:
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    signature = _sign_payload(body)
    if signature:
        headers["X-Yopa-Signature"] = signature
    try:
        requests.post(url, data=body, headers=headers, timeout=10)
    except Exception:
        pass
