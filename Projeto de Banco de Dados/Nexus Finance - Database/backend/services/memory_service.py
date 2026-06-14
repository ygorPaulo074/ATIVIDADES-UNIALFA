import json
import os
import time
import uuid

import redis

# Camada de IA é EFÊMERA: os chats vivem no Redis e expiram em 24h.
# Cada escrita renova o TTL, então a janela conta a partir da última atividade.
TTL_SEGUNDOS = 24 * 60 * 60  # 24h

_redis = redis.Redis.from_url(
    os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    decode_responses=True,
)


def _key(chat_id: str) -> str:
    return f"chat:{chat_id}"


def _load(chat_id: str) -> dict | None:
    raw = _redis.get(_key(chat_id))
    return json.loads(raw) if raw else None


def _save(chat_id: str, dados: dict) -> None:
    # ex=TTL renova a expiração de 24h a cada gravação
    _redis.set(_key(chat_id), json.dumps(dados, ensure_ascii=False), ex=TTL_SEGUNDOS)


def criar_chat() -> dict:
    """Cria um chat vazio no Redis (TTL 24h) e retorna id e nome inicial."""
    chat_id = str(uuid.uuid4())
    _save(chat_id, {"name": "Novo chat", "messages": [], "extrato": None, "created_at": time.time()})
    return {"id": chat_id, "name": "Novo chat"}


def listar_chats() -> list:
    """Lista os chats vivos no Redis como { id, name }, ordenados por criação."""
    chats = []
    for key in _redis.scan_iter(match="chat:*"):
        raw = _redis.get(key)
        if not raw:
            continue
        dados = json.loads(raw)
        chats.append({"id": key.split(":", 1)[1], "name": dados["name"], "_c": dados.get("created_at", 0)})
    chats.sort(key=lambda c: c["_c"])
    return [{"id": c["id"], "name": c["name"]} for c in chats]


def excluir_chat(chat_id: str) -> bool:
    """Remove o chat. Retorna True se existia."""
    return _redis.delete(_key(chat_id)) > 0


def add_message(chat_id: str, role: str, content: str) -> None:
    """Acrescenta uma mensagem; na 1ª do usuário define o nome do chat (40 chars)."""
    dados = _load(chat_id)
    if dados is None:
        return

    mensagens = dados["messages"]
    eh_primeira_mensagem_usuario = role == "user" and not any(m["role"] == "user" for m in mensagens)
    if eh_primeira_mensagem_usuario:
        dados["name"] = content[:40] + ("..." if len(content) > 40 else "")

    mensagens.append({"role": role, "content": content})
    _save(chat_id, dados)


def get_history(chat_id: str) -> list:
    """Histórico de mensagens do chat (lista vazia se expirado/inexistente)."""
    dados = _load(chat_id)
    return list(dados["messages"]) if dados else []


def get_chat_name(chat_id: str) -> str:
    dados = _load(chat_id)
    return dados["name"] if dados else ""


def set_extrato(chat_id: str, texto: str) -> None:
    """Armazena o extrato formatado do chat (substitui o anterior)."""
    dados = _load(chat_id)
    if dados is None:
        return
    dados["extrato"] = texto
    _save(chat_id, dados)


def clear_extrato(chat_id: str) -> None:
    dados = _load(chat_id)
    if dados is None:
        return
    dados["extrato"] = None
    _save(chat_id, dados)


def get_extrato(chat_id: str) -> str | None:
    """Extrato do chat ou None. Usado pelo groq_service para injetar contexto."""
    dados = _load(chat_id)
    return dados["extrato"] if dados else None
