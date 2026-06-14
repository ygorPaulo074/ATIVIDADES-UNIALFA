from fastapi import APIRouter, Header, HTTPException
from psycopg import errors as pg_errors

from models.auth import LoginIn, RegisterIn
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Token ausente")
    return authorization.split(" ", 1)[1]


@router.post("/register")
def register(data: RegisterIn):
    try:
        auth_service.register(data.username, data.password, data.email)
    except pg_errors.UniqueViolation:
        raise HTTPException(status_code=409, detail="Usuário já cadastrado")
    return {"ok": True, "message": "Conta criada. Você já pode entrar."}


@router.post("/login")
def login(data: LoginIn):
    token, err = auth_service.login(data.identifier, data.password)
    if err:
        raise HTTPException(status_code=401, detail=err)
    return {"token": token}


@router.get("/me")
def me(authorization: str | None = Header(default=None)):
    user = auth_service.get_session_user(_bearer(authorization))
    if not user:
        raise HTTPException(status_code=401, detail="Sessão inválida ou expirada")
    return user


@router.post("/logout")
def logout(authorization: str | None = Header(default=None)):
    auth_service.logout(_bearer(authorization))
    return {"ok": True}
