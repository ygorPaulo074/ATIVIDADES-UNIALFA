"""
Manages agent context versioning.
Each create or update persists an AgentContextRecord with an incremented version,
records the changed fields in changes and keeps the system prompt in sync in Redis.
"""
from datetime import datetime, timezone

from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.persistence.base import PersistenceDriver
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.security import encrypt_secret
from src.application.context_builder import build_system_prompt
from src.domain.agent import AgentContextBase, AgentContextRecord, SqlDatasourceConfig


class ContextService:

    def __init__(self):
        self.driver: PersistenceDriver = get_driver()
        self.cache = CacheClient()

    def _encrypt_sql_credentials(self, context: AgentContextBase) -> AgentContextBase:
        if not context.sql_datasource:
            return context
        enc = encrypt_secret(context.sql_datasource.connection_string)
        updated_sql = SqlDatasourceConfig(
            connection_string=enc,
            allowed_tables=context.sql_datasource.allowed_tables,
            max_rows=context.sql_datasource.max_rows,
        )
        return context.model_copy(update={"sql_datasource": updated_sql})

    def create_context(self, agent_id: str, context: AgentContextBase) -> None:
        context = self._encrypt_sql_credentials(context)
        now = datetime.now(timezone.utc).isoformat()
        system_prompt = build_system_prompt(context)
        record = AgentContextRecord(
            agent_id=agent_id,
            version=1,
            context=AgentContextBase(**context.model_dump()),
            changes=[],
            updated_at=now,
        )
        self.driver.save_context(record)
        self.cache.set_context(agent_id, system_prompt)

    def update_context(self, agent_id: str, new_context: AgentContextBase) -> AgentContextRecord:
        new_context = self._encrypt_sql_credentials(new_context)
        current = self.driver.load_context(agent_id)
        current_version = current.version if current else 0
        current_base = current.context if current else None

        changes = self.diff_context(current_base, new_context) if current_base else []

        record = AgentContextRecord(
            agent_id=agent_id,
            version=current_version + 1,
            context=AgentContextBase(**new_context.model_dump()),
            changes=changes,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        self.driver.save_context(record)

        system_prompt = build_system_prompt(new_context)
        self.cache.set_context(agent_id, system_prompt)

        return record

    def load_context(self, agent_id: str) -> AgentContextRecord | None:
        return self.driver.load_context(agent_id)

    def load_system_prompt(self, agent_id: str) -> str | None:
        cached = self.cache.get_context(agent_id)
        if cached:
            return cached
        record = self.driver.load_context(agent_id)
        if not record:
            return None
        system_prompt = build_system_prompt(AgentContextBase(**record.context.model_dump()))
        self.cache.set_context(agent_id, system_prompt)
        return system_prompt

    def load_context_history(self, agent_id: str) -> list[AgentContextRecord]:
        return self.driver.load_context_history(agent_id)

    def diff_context(self, old: AgentContextBase, new: AgentContextBase) -> list[str]:
        old_data = old.model_dump()
        new_data = new.model_dump()
        return [field for field in new_data if new_data[field] != old_data.get(field)]
