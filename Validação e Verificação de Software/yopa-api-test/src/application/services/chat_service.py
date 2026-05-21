"""
Orchestrates AI model calls for the POST /chat cycle.
Loads the system prompt from cache via ContextService, maintains history and scores in Redis,
runs the tool-use loop via AIClient and persists an incremental snapshot per message.
Supports per-agent credentials (BYOK): reads ai_model and ai_api_key from AgentRecord;
falls back to the global AI_MODEL/AI_API_KEY settings.
"""
import uuid
import time
import json
from datetime import datetime, timezone

from src.infrastructure.ai.client import AIClient
from src.infrastructure.cache.redis_client import CacheClient
from src.infrastructure.persistence.factory import get_driver
from src.infrastructure.security import decrypt_secret, sanitize_pii
from src.infrastructure.config import settings
from src.infrastructure.tools.file_tool import FileTool, TOOL_DEFINITION as FILE_TOOL_DEF
from src.infrastructure.tools.api_tool import ApiTool, TOOL_DEFINITION as API_TOOL_DEF
from src.infrastructure.tools.webhook_tool import WebhookTool, TOOL_DEFINITION as WEBHOOK_TOOL_DEF
from src.infrastructure.tools.sql_tool import SqlTool
from src.infrastructure.nlp import analyzer as quality_analyzer
from src.domain.conversation import HistoryMessage, SessionMeta, SessionRecord
from src.application.services.context_service import ContextService


class ChatService:

    def __init__(self):
        self.ai_client = AIClient()
        self.cache = CacheClient()
        self.context_service = ContextService()

    def _agent_credentials(self, agent_id: str) -> tuple[str, str | None]:
        driver = get_driver()
        agent = driver.load_agent(agent_id)
        model = (agent.ai_model if agent else None) or settings.AI_MODEL
        api_key = None
        if agent and agent.ai_api_key:
            api_key = decrypt_secret(agent.ai_api_key)
        elif settings.AI_API_KEY:
            api_key = settings.AI_API_KEY
        return model, api_key

    def process_message(self, agent_id: str, session_id: str, user_id: str | None, message: str) -> dict:
        model, api_key = self._agent_credentials(agent_id)
        system_prompt = self.context_service.load_system_prompt(agent_id) or ""
        history = self.cache.get_history(session_id)

        clean_message = sanitize_pii(message)

        now = datetime.now(timezone.utc).isoformat()
        user_msg_id = str(uuid.uuid4())
        user_msg = HistoryMessage(
            message_id=user_msg_id, session_id=session_id, role="user",
            content=clean_message, timestamp=now, status="delivered",
        )
        self.cache.append_message(session_id, user_msg)

        threshold = self._sentiment_threshold(agent_id)
        user_score = quality_analyzer.analyze(user_msg_id, "user", clean_message, threshold)

        tools, tool_executor = self._build_tools(agent_id)

        t0 = time.monotonic()
        ai_response = self.ai_client.complete(
            system=system_prompt,
            messages=history + [user_msg],
            tools=tools or None,
            tool_executor=tool_executor or None,
            model=model,
            api_key=api_key,
        )
        response_time_ms = int((time.monotonic() - t0) * 1000)

        reply_now = datetime.now(timezone.utc).isoformat()
        assistant_msg_id = str(uuid.uuid4())
        assistant_msg = HistoryMessage(
            message_id=assistant_msg_id, session_id=session_id, role="assistant",
            content=ai_response.content, timestamp=reply_now, status="delivered",
            tokens=ai_response.usage.output_tokens, response_time_ms=response_time_ms,
        )
        self.cache.append_message(session_id, assistant_msg)

        assistant_score = quality_analyzer.analyze(assistant_msg_id, "assistant", ai_response.content, threshold)
        existing_scores = self.cache.get_scores(session_id)
        scores = quality_analyzer.update_session_scores(session_id, existing_scores, user_score, now, threshold)
        scores = quality_analyzer.update_session_scores(session_id, scores, assistant_score, reply_now, threshold)

        prev_rt = [m.response_time_ms for m in history if m.role == "assistant" and m.response_time_ms is not None]
        all_rt = prev_rt + [response_time_ms]
        scores = scores.model_copy(update={"avg_response_time_ms": round(sum(all_rt) / len(all_rt), 1)})
        self.cache.set_scores(session_id, scores)

        meta = self.cache.get_session_meta(session_id)
        if meta is None:
            meta = SessionMeta(session_id=session_id, agent_id=agent_id, user_id=user_id, model=model, started_at=now)
        meta = meta.model_copy(update={
            "total_messages": meta.total_messages + 2,
            "input_tokens": meta.input_tokens + ai_response.usage.input_tokens,
            "output_tokens": meta.output_tokens + ai_response.usage.output_tokens,
            "total_tokens": meta.total_tokens + ai_response.usage.total_tokens,
        })
        self.cache.set_session_meta(session_id, meta)
        if self.cache.is_ephemeral_agent(agent_id):
            self.cache.add_ephemeral_session(agent_id, session_id)
        self._persist_snapshot(agent_id, session_id, meta, scores)

        return {
            "message_id": assistant_msg_id,
            "content": ai_response.content,
            "usage": ai_response.usage.model_dump(),
            "response_time_ms": response_time_ms,
        }

    def evaluate_escalation(self, agent_id: str, session_id: str) -> bool:
        record = self.context_service.load_context(agent_id)
        if not record or not record.context.escalation_trigger:
            return False
        trigger = record.context.escalation_trigger
        history = self.cache.get_history(session_id)
        scores = self.cache.get_scores(session_id)
        meta = self.cache.get_session_meta(session_id)
        results = [self._eval_condition(cond, history, scores, meta) for cond in trigger.conditions]
        return any(results) if trigger.operator == "OR" else all(results)

    def get_fallback_message(self, agent_id: str) -> str | None:
        record = self.context_service.load_context(agent_id)
        if not record:
            return None
        return record.context.fallback_message

    def _persist_snapshot(self, agent_id: str, session_id: str, meta: SessionMeta, scores) -> None:
        if self.cache.is_ephemeral_agent(agent_id):
            return
        driver = get_driver()
        driver.save_session(SessionRecord(
            session_id=meta.session_id, agent_id=agent_id, user_id=meta.user_id, model=meta.model,
            started_at=meta.started_at, ended_at=meta.ended_at, total_messages=meta.total_messages,
            input_tokens=meta.input_tokens, output_tokens=meta.output_tokens, total_tokens=meta.total_tokens,
            resolved=meta.resolved, escalated=meta.escalated,
        ))
        if scores:
            driver.save_scores(agent_id, scores)
        history = self.cache.get_history(session_id)
        if history:
            driver.save_history(agent_id, session_id, history)

    def _build_tools(self, agent_id: str):
        record = self.context_service.load_context(agent_id)
        context = record.context if record else None
        driver = get_driver()
        files = driver.list_knowledge_files(agent_id)
        all_records = [r for f in files for r in f.records]

        api_cfg = context.api_datasource if context else None
        webhook_cfg = context.webhook_datasource if context else None
        sql_cfg = context.sql_datasource if context else None
        has_files = bool(all_records)

        if not api_cfg and not webhook_cfg and not sql_cfg and not has_files:
            return [], None

        file_tool = FileTool(all_records) if has_files else None
        api_tool = ApiTool(url=api_cfg.url, token=api_cfg.token, query_param=api_cfg.query_param) if api_cfg else None
        webhook_tool = WebhookTool(url=webhook_cfg.url, token=webhook_cfg.token) if webhook_cfg else None
        sql_tool = (
            SqlTool(connection_string_enc=sql_cfg.connection_string, agent_id=agent_id,
                    allowed_tables=sql_cfg.allowed_tables, max_rows=sql_cfg.max_rows)
            if sql_cfg else None
        )
        fallback_msg = (context.fallback_message if context else None) or "Service temporarily unavailable."

        tools = []
        if webhook_tool:
            tools.append(WEBHOOK_TOOL_DEF)
        if api_tool:
            tools.append(API_TOOL_DEF)
        if sql_tool:
            tools.append(sql_tool.get_tool_definition())
        if file_tool:
            tools.append(FILE_TOOL_DEF)

        def executor(name: str, args_json: str) -> str:
            args = json.loads(args_json)
            query = args.get("query", "")
            if name == "search_webhook":
                try:
                    return webhook_tool.execute(query)
                except TimeoutError:
                    if file_tool:
                        result = file_tool.execute(query)
                        if result and "No relevant" not in result:
                            return result
                    return fallback_msg
                except RuntimeError:
                    return fallback_msg
            if name == "search_api":
                try:
                    return api_tool.execute(query)
                except TimeoutError:
                    if file_tool:
                        result = file_tool.execute(query)
                        if result and "No relevant" not in result:
                            return result
                    return fallback_msg
                except RuntimeError:
                    return fallback_msg
            if name == "query_database":
                try:
                    return sql_tool.execute(args.get("sql", ""))
                except (ValueError, TimeoutError, RuntimeError):
                    return fallback_msg
            if name == "search_knowledge_base":
                return file_tool.execute(query) if file_tool else fallback_msg
            return "Tool not found."

        return tools, executor

    def _sentiment_threshold(self, agent_id: str) -> float:
        record = self.context_service.load_context(agent_id)
        if not record or not record.context.escalation_trigger:
            return 0.3
        for cond in record.context.escalation_trigger.conditions:
            if cond.type == "sentiment" and cond.threshold is not None:
                return cond.threshold
        return 0.3

    def _eval_condition(self, cond, history: list[HistoryMessage], scores, meta: SessionMeta | None) -> bool:
        user_messages = [m for m in history if m.role == "user"]
        if cond.type == "keyword":
            keywords = cond.values or ([cond.value] if cond.value else [])
            if not user_messages or not keywords:
                return False
            last = user_messages[-1].content.lower()
            return any(str(kw).lower() in last for kw in keywords)
        if cond.type == "sentiment":
            if not scores or scores.avg_sentiment_score is None:
                return False
            threshold = cond.threshold if cond.threshold is not None else 0.3
            return scores.avg_sentiment_score < -threshold
        if cond.type == "message_count":
            return len(user_messages) >= int(cond.value or 0)
        if cond.type == "topic":
            topics = cond.values or ([cond.value] if cond.value else [])
            if not scores or not topics:
                return False
            return any(t in (scores.all_topics or []) for t in topics)
        if cond.type == "time_elapsed":
            if not meta or cond.value is None:
                return False
            started = datetime.fromisoformat(meta.started_at)
            elapsed = (datetime.now(timezone.utc) - started).total_seconds()
            return elapsed >= float(cond.value)
        if cond.type == "intent":
            if not scores or not cond.value:
                return False
            return scores.intent == cond.value
        return False
