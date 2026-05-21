"""
SqlTool — runs SELECT queries against a database configured by the agent.

5 security layers:
  1. Dialect allowlist (postgresql, mysql, sqlite — configurable)
  2. Encrypted credentials (Fernet via security.encrypt_secret)
  3. SELECT-only enforcement (sqlparse — rejects DDL/DML)
  4. Execution timeout (settings.SQL_QUERY_TIMEOUT seconds)
  5. Per-agent audit log (data/agents/{agent_id}/sql_audit.jsonl)
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import sqlparse
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, TimeoutError as SATimeoutError

from src.infrastructure.config import settings
from src.infrastructure.security import decrypt_secret


def validate_connection_string(conn_str: str) -> str:
    try:
        parsed = urlparse(conn_str)
        dialect = parsed.scheme.split("+")[0].lower()
    except Exception as exc:
        raise ValueError(f"Connection string inválida: {exc}") from exc

    if not dialect:
        raise ValueError("Connection string sem esquema (ex: postgresql://...).")

    allowed = [d.lower() for d in settings.SQL_ALLOWED_DIALECTS]
    if dialect not in allowed:
        raise ValueError(f"Dialeto '{dialect}' não permitido. Permitidos: {', '.join(allowed)}.")

    if not parsed.hostname and dialect != "sqlite":
        raise ValueError("Connection string sem host.")

    return conn_str


def _validate_sql(sql: str) -> str:
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        raise ValueError("Múltiplos statements não permitidos.")
    parsed = sqlparse.parse(sql)
    if not parsed:
        raise ValueError("SQL vazio ou inválido.")
    stmt_type = parsed[0].get_type()
    if stmt_type != "SELECT":
        raise ValueError(f"Apenas SELECT é permitido. Recebido: {stmt_type or 'desconhecido'}.")
    return sql


def _audit(agent_id: str, sql: str, rows: int, duration_ms: int, error: str | None) -> None:
    try:
        audit_dir = Path(settings.DATA_PATH) / "agents" / agent_id
        audit_dir.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "sql": sql[:200],
            "rows": rows,
            "duration_ms": duration_ms,
            "success": error is None,
            "error": error,
        }
        with open(audit_dir / "sql_audit.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


class SqlTool:

    def __init__(self, connection_string_enc: str, agent_id: str, allowed_tables: list[str] | None = None, max_rows: int | None = None):
        self._conn_str_enc = connection_string_enc
        self.agent_id = agent_id
        self.allowed_tables = allowed_tables or []
        self.max_rows = max_rows or settings.SQL_MAX_ROWS
        self._schema_cache: str | None = None

    def _connect_string(self) -> str:
        plaintext = decrypt_secret(self._conn_str_enc)
        return validate_connection_string(plaintext)

    def _get_schema(self) -> str:
        if self._schema_cache:
            return self._schema_cache
        conn_str = self._connect_string()
        engine = create_engine(conn_str, pool_pre_ping=True)
        try:
            from sqlalchemy import inspect
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if self.allowed_tables:
                tables = [t for t in tables if t in self.allowed_tables]
            parts = []
            for table in tables[:20]:
                try:
                    cols = inspector.get_columns(table)
                    col_str = ", ".join(f"{c['name']} ({c['type']})" for c in cols)
                    parts.append(f"{table}({col_str})")
                except Exception:
                    parts.append(table)
            self._schema_cache = "; ".join(parts) if parts else "schema indisponível"
        except Exception as exc:
            self._schema_cache = f"schema indisponível ({exc})"
        finally:
            engine.dispose()
        return self._schema_cache

    def get_tool_definition(self) -> dict:
        schema = self._get_schema()
        return {
            "type": "function",
            "function": {
                "name": "query_database",
                "description": (
                    f"Execute a SQL SELECT query against the configured database. "
                    f"Available tables: {schema}. "
                    "Only SELECT statements are allowed. Return relevant rows."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {"sql": {"type": "string", "description": "A single SQL SELECT statement."}},
                    "required": ["sql"],
                },
            },
        }

    def execute(self, sql: str) -> str:
        safe_sql = _validate_sql(sql)
        conn_str = self._connect_string()
        engine = create_engine(conn_str, pool_pre_ping=True, connect_args=self._timeout_args(conn_str))
        t0 = time.monotonic()
        rows_count = 0
        error_msg = None
        try:
            with engine.connect() as conn:
                result = conn.execute(text(safe_sql), execution_options={"timeout": settings.SQL_QUERY_TIMEOUT})
                rows = result.fetchmany(self.max_rows)
                cols = list(result.keys())
                rows_count = len(rows)
            formatted = self._format(cols, rows)
        except SATimeoutError as exc:
            error_msg = "timeout"
            raise TimeoutError("Query excedeu o tempo limite de execução.") from exc
        except OperationalError as exc:
            error_msg = str(exc)[:100]
            raise RuntimeError(f"Erro ao executar query: {exc}") from exc
        except Exception as exc:
            error_msg = str(exc)[:100]
            raise RuntimeError(f"Erro inesperado na query: {exc}") from exc
        finally:
            duration_ms = int((time.monotonic() - t0) * 1000)
            engine.dispose()
            _audit(self.agent_id, sql, rows_count, duration_ms, error_msg)
        return formatted

    @staticmethod
    def _timeout_args(conn_str: str) -> dict:
        dialect = urlparse(conn_str).scheme.split("+")[0].lower()
        if dialect == "postgresql":
            return {"options": f"-c statement_timeout={settings.SQL_QUERY_TIMEOUT * 1000}"}
        if dialect == "mysql":
            return {"connect_timeout": settings.SQL_QUERY_TIMEOUT}
        return {}

    @staticmethod
    def _format(cols: list[str], rows: list) -> str:
        if not rows:
            return "No results found."
        lines = [" | ".join(cols)]
        for row in rows:
            lines.append(" | ".join(str(v) if v is not None else "" for v in row))
        return "\n".join(lines)
