import secrets
from datetime import datetime, timedelta, timezone

import bcrypt

from services import db_service as db

SESSION_DAYS = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def new_token() -> str:
    return secrets.token_urlsafe(32)


# --- Cadastro ---

def register(username: str, password: str, email: str | None = None) -> int:
    """Cria o usuário (já ativo) e semeia as categorias padrão. Retorna o id."""
    row = db.query_one(
        "INSERT INTO users(username, email, password_hash) VALUES (%s, %s, %s) RETURNING id",
        (username, email, hash_password(password)),
    )
    user_id = row["id"]
    db.execute("SELECT seed_default_categories(%s)", (user_id,))
    return user_id


# --- Login / sessão ---

def login(identifier: str, password: str) -> tuple[str | None, str | None]:
    """Login por username (ou email, se informado). Retorna (token_de_sessao, erro)."""
    field = "email" if "@" in identifier else "username"
    user = db.query_one(f"SELECT * FROM users WHERE {field} = %s", (identifier,))
    if not user or not verify_password(password, user["password_hash"]):
        return None, "Credenciais inválidas"

    token = new_token()
    db.execute(
        "INSERT INTO sessions(user_id, token, expires_at) VALUES (%s, %s, %s)",
        (user["id"], token, _now() + timedelta(days=SESSION_DAYS)),
    )
    return token, None


def get_session_user(token: str) -> dict | None:
    """Valida a sessão e desliza a expiração (30 dias). Retorna o usuário ou None."""
    row = db.query_one(
        """SELECT s.id AS sid, s.expires_at, u.id, u.username, u.email
           FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token = %s""",
        (token,),
    )
    if not row or row["expires_at"] < _now():
        return None
    db.execute(
        "UPDATE sessions SET expires_at = %s WHERE id = %s",
        (_now() + timedelta(days=SESSION_DAYS), row["sid"]),
    )
    return {"id": row["id"], "username": row["username"], "email": row["email"]}


def logout(token: str) -> None:
    db.execute("DELETE FROM sessions WHERE token = %s", (token,))
