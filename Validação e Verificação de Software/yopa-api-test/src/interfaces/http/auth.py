"""
FastAPI dependency for agent authentication — supports two modes via AUTH_MODE:

  standalone: Bearer {agent_id}.{secret} in the Authorization header.
              Used in direct deploys without the Yopa Proxy.

  internal:   X-Agent-Id injected by the Yopa Proxy after api_key validation.
              The API trusts the header without re-validating credentials — the proxy
              is the sole entry point and has already authenticated before forwarding.
"""
from fastapi import HTTPException, Request, status

from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.security import verify_api_key
from src.infrastructure.config import settings


async def authenticate_agent(request: Request) -> str:
    if settings.AUTH_MODE == "internal":
        agent_id = request.headers.get("X-Agent-Id", "")
        if not agent_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return agent_id

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    api_key = auth_header[7:]
    try:
        agent_id, secret = api_key.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    agent = get_driver().load_agent(agent_id)
    if agent:
        if not verify_api_key(secret, agent.api_key_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        return agent_id

    from src.infrastructure.cache.redis_client import CacheClient
    ephemeral = CacheClient().get_ephemeral_agent(agent_id)
    if ephemeral and verify_api_key(secret, ephemeral["secret_hash"]):
        return agent_id

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
