"""
Request and response schemas for /agent endpoints — creation, retrieval, context,
knowledge base, AI/SQL validation and free-text context parsing.
"""
from pydantic import BaseModel
from src.domain.agent import AgentContextBase


class AgentCreateRequest(BaseModel):
    name: str
    owner: str
    context: AgentContextBase
    ai_model: str | None = None
    ai_api_key: str | None = None


class AgentCreateResponse(BaseModel):
    agent_id: str
    api_key: str
    created_at: str


class AgentGetResponse(BaseModel):
    agent_id: str
    name: str
    owner: str
    created_at: str
    updated_at: str
    active_since: str | None = None
    last_activity_at: str | None = None
    ai_model: str | None = None
    ai_validated: bool = False


class AgentPatchRequest(BaseModel):
    name: str


class AgentPatchResponse(BaseModel):
    agent_id: str
    name: str
    updated_at: str


class AgentContextResponse(AgentContextBase):
    agent_id: str
    version: int


class AgentContextHistoryItem(BaseModel):
    version: int
    updated_at: str
    changes: list[str]


class AgentContextHistoryResponse(BaseModel):
    agent_id: str
    versions: list[AgentContextHistoryItem]


class AgentMetricsResponse(BaseModel):
    agent_id: str
    total_sessions: int
    total_messages: int
    total_tokens: int
    resolution_rate: float
    escalation_rate: float
    active_since: str | None = None
    last_activity_at: str | None = None


class AgentUpdateContextResponse(BaseModel):
    agent_id: str
    version: int
    updated_at: str


class AgentDeleteResponse(BaseModel):
    deleted_at: str


class KnowledgeFileUploadResponse(BaseModel):
    file_id: str
    filename: str
    file_type: str
    record_count: int
    uploaded_at: str


class KnowledgeFileItem(BaseModel):
    file_id: str
    filename: str
    file_type: str
    record_count: int
    uploaded_at: str
    updated_at: str


class KnowledgeFileListResponse(BaseModel):
    files: list[KnowledgeFileItem]


class KnowledgeFileDeleteResponse(BaseModel):
    file_id: str
    deleted: bool


class KnowledgeFetchUrlRequest(BaseModel):
    url: str


class ParseContextRequest(BaseModel):
    text: str


class ParseContextResponse(BaseModel):
    context: AgentContextBase


class ValidateSqlRequest(BaseModel):
    connection_string: str


class ValidateSqlResponse(BaseModel):
    valid: bool
    dialect: str | None = None
    tables: list[str] = []
    error: str | None = None


class ValidateAIResponse(BaseModel):
    valid: bool
    model: str | None = None
    error: str | None = None
