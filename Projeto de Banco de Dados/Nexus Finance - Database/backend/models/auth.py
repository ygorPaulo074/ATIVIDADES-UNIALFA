from pydantic import BaseModel


class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None  # opcional (sem auth por email)


class LoginIn(BaseModel):
    identifier: str  # username (ou email, se houver)
    password: str
