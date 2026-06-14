from typing import Callable

from fastapi import Header, HTTPException
from psycopg import errors as pg

from services import auth_service


def current_user(authorization: str | None = Header(default=None)) -> dict:
    """Dependência: exige sessão válida (header Authorization: Bearer <token>)."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    user = auth_service.get_session_user(authorization.split(" ", 1)[1])
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return user


def guard(fn: Callable):
    """Traduz erros do banco (triggers/constraints) em respostas HTTP."""
    try:
        return fn()
    except PermissionError:
        raise HTTPException(status_code=403, detail="Recurso não pertence ao usuário")
    except pg.RaiseException as e:  # RAISE EXCEPTION dos triggers (ex.: limite de tags)
        raise HTTPException(status_code=400, detail=e.diag.message_primary or "Operação inválida")
    except pg.UniqueViolation:
        raise HTTPException(status_code=409, detail="Registro duplicado")
    except (pg.CheckViolation, pg.InvalidTextRepresentation) as e:
        raise HTTPException(status_code=400, detail=e.diag.message_primary or "Valor inválido")
