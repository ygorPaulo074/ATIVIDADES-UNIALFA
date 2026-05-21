"""
Factories de payloads para os testes.

Use estes helpers em vez de literais JSON espalhados nos testes — facilita
ajustar a forma do payload em um único lugar quando o schema muda.
"""
import uuid


def build_agent_payload(**overrides):
    """Payload padrão para POST /agent. Permite sobrescrever campos."""
    base = {
        "name": "Test Agent",
        "owner": "test_owner",
        "context": {
            "tone": "formal",
            "language": "pt",
            "persona": "Assistente de testes",
        },
    }
    base.update(overrides)
    return base


def build_chat_payload(**overrides):
    """Payload padrão para POST /chat. session_id é gerado se omitido."""
    base = {
        "session_id": str(uuid.uuid4()),
        "user_id": "user_123",
        "message": "Hello, I need help.",
    }
    base.update(overrides)
    return base


def build_context_update_payload(**overrides):
    """Payload padrão para PUT /agent/context."""
    base = {
        "tone": "informal",
        "language": "pt",
    }
    base.update(overrides)
    return base
