"""
Admin endpoints — require X-Internal-Token; not exposed to end users.
  GET  /health         — liveness + readiness (no auth)
  POST /admin/purge    — hard-delete agents and sessions with deleted_at < before
"""
import hmac
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel

from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.config import settings

router = APIRouter(tags=["admin"])


def _require_internal(request: Request) -> None:
    token = request.headers.get("X-Internal-Token", "")
    if not settings.INTERNAL_TOKEN or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    if not hmac.compare_digest(token, settings.INTERNAL_TOKEN):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")


class PurgeRequest(BaseModel):
    before: str


class PurgeResponse(BaseModel):
    agents_purged: int
    sessions_purged: int


@router.post("/admin/purge", response_model=PurgeResponse)
def purge_deleted(body: PurgeRequest, request: Request):
    _require_internal(request)
    result = get_driver().purge_deleted(body.before)
    return PurgeResponse(
        agents_purged=result.get("agents_purged", 0),
        sessions_purged=result.get("sessions_purged", 0),
    )
