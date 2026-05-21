"""
Parte 1 — Módulo: src/infrastructure/tools/sql_tool.py

ESCOPO
------
SqlTool — executa SELECT contra banco configurado pelo agente, com 5 camadas
de segurança:
1. Validação de dialeto (validate_connection_string)
2. Criptografia em repouso (encrypt_secret — testado em test_security)
3. SELECT-only (_validate_sql)
4. Timeout / max rows
5. Audit log por agente

TIPOS DE TESTE
--------------
- unit         : validate_connection_string, _validate_sql
- integration  : SqlTool.execute contra SQLite em memória
- regression   : rejeita INSERT/UPDATE/DELETE/DROP/multiple
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text as stext

from tests.shared.log_helper import logged

from src.infrastructure.tools.sql_tool import (
    validate_connection_string,
    _validate_sql,
    SqlTool,
)
from src.infrastructure.security import encrypt_secret


@pytest.mark.unit
@pytest.mark.part1
class TestValidateConnectionString:
    """Camada 1 — dialeto permitido."""

    @logged
    def test_accepts_postgresql(self):
        url = "postgresql://user:pass@localhost/db"
        assert validate_connection_string(url) == url

    @logged
    def test_accepts_mysql(self):
        url = "mysql://user:pass@localhost/db"
        assert validate_connection_string(url) == url

    @logged
    def test_accepts_sqlite_without_host(self):
        """SQLite é dialeto local — não exige hostname."""
        url = "sqlite:///tmp/test.db"
        assert validate_connection_string(url) == url

    @logged
    def test_rejects_mssql(self):
        with pytest.raises(ValueError, match="não permitido"):
            validate_connection_string("mssql://user:pass@host/db")

    @logged
    def test_rejects_string_without_scheme(self):
        with pytest.raises(ValueError):
            validate_connection_string("isso-nao-eh-url")


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.part1
class TestValidateSql:
    """Camada 3 — SELECT-only, single statement."""

    @logged
    def test_select_passes(self):
        assert _validate_sql("SELECT id FROM users") == "SELECT id FROM users"

    @logged
    def test_select_with_trailing_semicolon_is_normalized(self):
        """O ';' final é removido — single statement ainda é válido."""
        assert _validate_sql("SELECT 1;") == "SELECT 1"

    @logged
    def test_insert_rejected(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("INSERT INTO t VALUES (1)")

    @logged
    def test_update_rejected(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("UPDATE t SET x = 1")

    @logged
    def test_delete_rejected(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("DELETE FROM t")

    @logged
    def test_drop_rejected(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("DROP TABLE t")

    @logged
    def test_multiple_statements_rejected(self):
        """'SELECT 1; DROP TABLE users' deve ser bloqueado."""
        with pytest.raises(ValueError, match="Múltiplos"):
            _validate_sql("SELECT 1; DROP TABLE users")


@pytest.mark.integration
@pytest.mark.part1
class TestSqlToolExecute:
    """Camadas 4-5 — execução real em SQLite + audit log."""

    def _make_tool_with_db(self, tmp_path, agent_id="agent-x"):
        """Cria SQLite em arquivo e retorna SqlTool apontando para ele."""
        db_path = tmp_path / "test.db"
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.begin() as conn:
            conn.execute(stext("CREATE TABLE produtos (id INTEGER, nome TEXT)"))
            conn.execute(stext("INSERT INTO produtos VALUES (1, 'Widget A')"))
            conn.execute(stext("INSERT INTO produtos VALUES (2, 'Widget B')"))
        engine.dispose()
        return SqlTool(
            connection_string_enc=encrypt_secret(f"sqlite:///{db_path}"),
            agent_id=agent_id,
        )

    @logged
    def test_execute_returns_results(self, tmp_path):
        tool = self._make_tool_with_db(tmp_path)
        result = tool.execute("SELECT id, nome FROM produtos")
        assert "Widget A" in result
        assert "Widget B" in result

    @logged
    def test_execute_empty_result_returns_no_results(self, tmp_path):
        tool = self._make_tool_with_db(tmp_path)
        result = tool.execute("SELECT id, nome FROM produtos WHERE id > 999")
        assert "No results found." in result

    @logged
    def test_execute_rejects_invalid_sql(self, tmp_path):
        tool = self._make_tool_with_db(tmp_path)
        with pytest.raises(ValueError):
            tool.execute("DELETE FROM produtos")

    @logged
    def test_audit_log_written_on_success(self, tmp_path):
        """Cada execução deve gerar uma linha jsonl no audit log do agente."""
        tool = self._make_tool_with_db(tmp_path, agent_id="audit-agent")
        tool.execute("SELECT id FROM produtos")

        # DATA_PATH é apontado para tmp_path pelo conftest (patch_env)
        from src.infrastructure.config import settings
        audit = Path(settings.DATA_PATH) / "agents" / "audit-agent" / "sql_audit.jsonl"
        assert audit.exists()
        line = audit.read_text(encoding="utf-8").strip().splitlines()[-1]
        entry = json.loads(line)
        assert entry["success"] is True
        assert "SELECT" in entry["sql"]

    @logged
    def test_audit_log_records_failure(self, tmp_path):
        tool = self._make_tool_with_db(tmp_path, agent_id="fail-agent")
        with pytest.raises(RuntimeError):
            tool.execute("SELECT inexistente FROM produtos")

        from src.infrastructure.config import settings
        audit = Path(settings.DATA_PATH) / "agents" / "fail-agent" / "sql_audit.jsonl"
        assert audit.exists()
        entry = json.loads(audit.read_text(encoding="utf-8").strip().splitlines()[-1])
        assert entry["success"] is False
        assert entry["error"] is not None
