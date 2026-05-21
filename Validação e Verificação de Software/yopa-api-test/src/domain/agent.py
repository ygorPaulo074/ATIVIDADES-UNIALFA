"""
Agent domain entities: identity, context configuration and escalation rules.
All URL fields are plain str — format validation is handled in the HTTP schemas layer.
"""
from typing import Any, Literal
from pydantic import BaseModel


class FileReference(BaseModel):
    name: str
    url: str


class RestrictionsConfig(BaseModel):
    topics: list[str] = []
    files: list[FileReference] = []


class KnowledgeBaseConfig(BaseModel):
    urls: list[str] = []
    files: list[FileReference] = []


class ApiDatasourceConfig(BaseModel):
    url: str
    token: str | None = None
    query_param: str = "q"


class WebhookDatasourceConfig(BaseModel):
    url: str
    token: str | None = None


class SqlDatasourceConfig(BaseModel):
    connection_string: str
    allowed_tables: list[str] = []
    max_rows: int = 50


class EscalationCondition(BaseModel):
    type: Literal["keyword", "sentiment", "message_count", "topic", "time_elapsed", "intent"]
    value: str | int | float | None = None
    values: list[str] | None = None
    threshold: float | None = None


class EscalationTrigger(BaseModel):
    operator: Literal["OR", "AND"]
    conditions: list[EscalationCondition]


class EscalationDestinationConfig(BaseModel):
    type: Literal["webhook", "email", "github_issue", "queue", "none"] = "none"
    url: str | None = None
    token: str | None = None
    address: str | None = None
    repo: str | None = None
    github_token: str | None = None
    queue_url: str | None = None


class AgentContextBase(BaseModel):
    tone: Literal["formal", "informal", "neutro"] | None = None
    language: str | None = None
    segment: str | None = None
    persona: str | None = None
    behavior: str | None = None
    fallback_message: str | None = None
    restrictions: RestrictionsConfig | None = None
    knowledge_base: KnowledgeBaseConfig | None = None
    escalation_trigger: EscalationTrigger | None = None
    escalation_destination: EscalationDestinationConfig | None = None
    api_datasource: ApiDatasourceConfig | None = None
    webhook_datasource: WebhookDatasourceConfig | None = None
    sql_datasource: SqlDatasourceConfig | None = None


class AgentRecord(BaseModel):
    agent_id: str
    name: str
    owner: str
    api_key_hash: str
    created_at: str
    updated_at: str
    active_since: str | None = None
    last_activity_at: str | None = None
    deleted_at: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_validated: bool = False


class AgentContextRecord(BaseModel):
    agent_id: str
    version: int
    context: AgentContextBase
    changes: list[str] = []
    updated_at: str


