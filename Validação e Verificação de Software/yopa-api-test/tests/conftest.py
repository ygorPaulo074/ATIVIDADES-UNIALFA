"""
Fixtures compartilhadas entre Parte 1 e Parte 2.

Este conftest é a base de toda a suite. Ele:
1. Define variáveis de ambiente ANTES de qualquer import do src/ — sem isso,
   o `pydantic-settings` levantaria erro por falta de AI_API_KEY, AI_MODEL etc.
2. Substitui o cliente Redis real por uma instância em memória (`fakeredis`).
3. Substitui `sanitize_pii` por uma identidade — Presidio carrega modelos
   pesados; em teste, não queremos que isso rode.
4. Disponibiliza fixtures `client`, `agent` e `mock_ai` usadas por part2/
   (e também por testes integrados de part1/ que tocam services).

A Parte 1 (testes unitários puros) pode IGNORAR a maioria destas fixtures
e importar diretamente o que precisa de `src/`.
"""
import os
import pytest
import fakeredis

# Logger da suite (gera arquivo em logs/ a cada rodada).
from tests.shared.log_helper import log_event, LOG_FILE


# ── Variáveis de ambiente — definidas ANTES de qualquer `from src...` ────────

os.environ.setdefault("AI_API_KEY", "test_key")
os.environ.setdefault("AI_MODEL", "gpt-4o")
os.environ.setdefault("AI_TIMEOUT", "30")
os.environ.setdefault("RUN_MODE", "development")
os.environ.setdefault("PORT", "8000")
os.environ.setdefault("STORAGE_TYPE", "local")
os.environ.setdefault("DATA_PATH", "/tmp/yopa_api_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SESSION_TTL", "86400")
os.environ.setdefault("ANALYZER_LANGUAGES", '["en"]')

# Sinaliza que o "wizard" interativo de setup já rodou (evita bloqueio).
open(".initialized", "w").close()

# Imports do `src/` precisam vir DEPOIS das env vars acima.
from unittest.mock import patch  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402
from src.infrastructure.ai.client import AIClient, AIResponse, AIUsage  # noqa: E402
from src.infrastructure.cache.redis_client import CacheClient  # noqa: E402
import src.infrastructure.security as _security  # noqa: E402


# ── Identidade no lugar do Presidio ──────────────────────────────────────────
# Em produção, sanitize_pii() roda Presidio para remover PII. Em testes, isso
# adicionaria 3-18ms por chamada sem necessidade — usamos identidade.
_security.sanitize_pii = lambda text: text


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def fake_redis_server():
    """Servidor fakeredis compartilhado pela sessão inteira de testes."""
    return fakeredis.FakeServer()


@pytest.fixture(autouse=True)
def patch_env(fake_redis_server, monkeypatch, tmp_path):
    """
    Aplica a TODOS os testes:
    - Substitui o CacheClient real por fakeredis.
    - Aponta DATA_PATH para um tmp_path isolado por teste.

    `autouse=True` garante isolamento mesmo nos testes que não pedem a fixture.
    """
    fake = fakeredis.FakeRedis(server=fake_redis_server, decode_responses=True)
    fake.flushall()

    def _fake_cache_init(self):
        self._redis = fake

    monkeypatch.setattr(CacheClient, "__init__", _fake_cache_init)

    from src.infrastructure.config import settings
    monkeypatch.setattr(settings, "DATA_PATH", str(tmp_path))


@pytest.fixture
def mock_ai():
    """
    Substitui AIClient.complete por uma resposta fixa.
    Evita chamada real ao LLM (custaria tokens e seria lento).
    """
    fake_response = AIResponse(
        content="Test response from AI.",
        usage=AIUsage(input_tokens=10, output_tokens=5, total_tokens=15),
    )
    with patch.object(AIClient, "complete", return_value=fake_response) as mock:
        yield mock


@pytest.fixture
def client(patch_env):
    """TestClient do Starlette — cliente HTTP em memória contra o app FastAPI."""
    from main import app
    return TestClient(app, raise_server_exceptions=True)


# ── Hooks de sessão pytest — geram log automático em logs/ ───────────────────

def pytest_sessionstart(session):
    """Logado no início da sessão pytest — antes de coletar os testes."""
    log_event("SESSION", f"Início da execução — arquivo: {LOG_FILE.name}")


def pytest_sessionfinish(session, exitstatus):
    """Logado no fim da sessão pytest — depois do último teste."""
    log_event("SESSION", f"Fim da execução — exit_status={exitstatus}")


def pytest_runtest_logreport(report):
    """
    Logado para cada fase (setup, call, teardown) de cada teste.
    Aqui só logamos a fase 'call' para evitar ruído com setup/teardown.

    Este hook complementa o decorator @logged. O decorator dá detalhes
    finos; este hook garante log mesmo nos testes que não usam @logged.
    """
    if report.when != "call":
        return
    if report.passed:
        return  # decorator @logged já registrou PASS detalhado
    # Casos não cobertos pelo decorator (ex: teste sem @logged que falhou):
    outcome = report.outcome.upper()
    log_event(outcome, f"{report.nodeid} (duration={report.duration*1000:.1f}ms)")


@pytest.fixture
def agent(client):
    """
    Cria um agente real via POST /agent e devolve (agent_id, api_key, headers).
    Usado em todos os testes da Parte 2 que precisam estar autenticados.
    """
    resp = client.post("/agent", json={
        "name": "Test Agent",
        "owner": "test_owner",
        "context": {
            "tone": "formal",
            "language": "pt",
            "persona": "Assistente de testes",
        },
    })
    assert resp.status_code == 201
    data = resp.json()
    headers = {"Authorization": f"Bearer {data['api_key']}"}
    return data["agent_id"], data["api_key"], headers
