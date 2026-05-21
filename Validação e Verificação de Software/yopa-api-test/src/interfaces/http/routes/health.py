from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse, JSONResponse

from src.infrastructure.config import settings

router = APIRouter(tags=["admin"])

_started_at: datetime = datetime.now(timezone.utc)
_checks: deque = deque(maxlen=50)

_STATIC = Path(__file__).parents[3] / "static"


@router.get("/health", include_in_schema=False)
def health_ui():
    return FileResponse(_STATIC / "health.html")


@router.get("/health/status")
def health_status():
    now = datetime.now(timezone.utc)
    uptime = (now - _started_at).total_seconds()
    _checks.append({
        "timestamp": now.isoformat(),
        "status": "ok",
        "uptime_seconds": round(uptime, 1),
    })
    return JSONResponse({
        "status": "ok",
        "version": settings.APP_VERSION,
        "started_at": _started_at.isoformat(),
        "uptime_seconds": round(uptime, 1),
        "storage": settings.STORAGE_TYPE,
        "recent_checks": list(_checks)[-20:],
    })
