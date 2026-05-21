"""
Sistema de logging para a suite de testes.

Gera um arquivo de log por execução em `logs/`, contendo:
  - Início e fim da sessão pytest
  - Cada teste: START, PASS/FAIL/SKIP, duração em ms
  - Mensagens manuais via `log_event(...)`

Componentes:
  - log_event(level, message)  → escreve uma linha no log da rodada atual
  - @logged                    → decorator para envolver funções de teste
  - LOG_FILE                   → Path do arquivo de log da rodada atual
  - LOG_DIR                    → Path do diretório logs/

Os hooks de sessão pytest ficam em `tests/conftest.py`.
"""
import functools
import time
from datetime import datetime
from pathlib import Path


LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
LOG_FILE = LOG_DIR / f"test_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"


def log_event(level: str, message: str) -> None:
    """
    Escreve uma linha no log da rodada atual.

    Formato: [ISO_TIMESTAMP] [LEVEL] MESSAGE
    Níveis sugeridos: SESSION, START, PASS, FAIL, SKIP, INFO, WARN.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="milliseconds")
    line = f"[{timestamp}] [{level:7}] {message}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def logged(func):
    """
    Decorator de logging para funções de teste.

    Loga:
      - START: nome qualificado do teste
      - PASS/FAIL/SKIP + duração em ms
      - Tipo e mensagem da exceção em caso de falha

    Uso:
        @logged
        def test_alguma_coisa(self):
            assert ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        test_name = f"{func.__module__}::{func.__qualname__}"
        log_event("START", test_name)
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except BaseException as exc:
            elapsed_ms = (time.perf_counter() - start) * 1000
            exc_name = type(exc).__name__
            # pytest.skip() levanta uma exceção interna chamada "Skipped"
            if exc_name in ("Skipped", "OutcomeException"):
                log_event("SKIP", f"{test_name} ({elapsed_ms:.1f}ms) — {exc}")
            else:
                log_event("FAIL", f"{test_name} ({elapsed_ms:.1f}ms) — {exc_name}: {exc}")
            raise
        elapsed_ms = (time.perf_counter() - start) * 1000
        log_event("PASS", f"{test_name} ({elapsed_ms:.1f}ms)")
        return result

    return wrapper
