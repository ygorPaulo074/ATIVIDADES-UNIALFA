import os

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

# Pool de conexões com o PostgreSQL. Na stack o host é "db".
# O backend chama as funções SQL (sem ORM) — ver db/functions/.
_pool = ConnectionPool(
    conninfo=os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/postgres"),
    min_size=1,
    max_size=10,
    open=True,
)


def query_all(sql: str, params: tuple = ()) -> list[dict]:
    """Executa um SELECT e retorna todas as linhas como dicts."""
    with _pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def query_one(sql: str, params: tuple = ()) -> dict | None:
    """Executa um SELECT e retorna a primeira linha (ou None)."""
    with _pool.connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    """Executa INSERT/UPDATE/DELETE/SELECT de função. Commit automático no fim do bloco."""
    with _pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
