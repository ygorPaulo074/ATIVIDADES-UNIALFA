"""
AI model connection via LiteLLM.
Abstracts the provider (Anthropic, OpenAI, Gemini, DeepSeek, Groq), handles
timeout and the tool-use loop. Supports per-agent credentials (BYOK): model and api_key
are optional — falls back to global settings if omitted.
"""
import json
import litellm
from typing import Callable
from pydantic import BaseModel

from src.infrastructure.config import settings
from src.domain.conversation import HistoryMessage


class AIUsage(BaseModel):
    input_tokens: int
    output_tokens: int
    total_tokens: int


class AIResponse(BaseModel):
    content: str
    usage: AIUsage


class AIClient:

    def complete(
        self,
        system: str,
        messages: list[HistoryMessage],
        tools: list[dict] | None = None,
        tool_executor: Callable[[str, str], str] | None = None,
        max_tokens: int = 1024,
        model: str | None = None,
        api_key: str | None = None,
    ) -> AIResponse:
        litellm_messages = [
            {"role": "system", "content": system},
            *[{"role": m.role, "content": m.content} for m in messages],
        ]
        total_input = 0
        total_output = 0

        resolved_model = model or settings.AI_MODEL
        resolved_key = api_key or settings.AI_API_KEY or None

        kwargs = dict(
            model=resolved_model,
            api_key=resolved_key,
            messages=litellm_messages,
            max_tokens=max_tokens,
            stream=False,
            timeout=settings.AI_TIMEOUT,
        )
        if tools:
            kwargs["tools"] = tools

        response = litellm.completion(**kwargs)
        raw_usage = getattr(response, "usage", None)
        total_input += raw_usage.prompt_tokens if raw_usage else 0
        total_output += raw_usage.completion_tokens if raw_usage else 0

        rounds = 0
        while rounds < settings.MAX_TOOL_ROUNDS:
            tool_calls = getattr(response.choices[0].message, "tool_calls", None)
            if not tool_calls or not tool_executor:
                break
            rounds += 1
            litellm_messages.append(response.choices[0].message.model_dump(exclude_none=True))
            for tc in tool_calls:
                args = json.loads(tc.function.arguments)
                result = tool_executor(tc.function.name, json.dumps(args))
                litellm_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
            kwargs["messages"] = litellm_messages
            response = litellm.completion(**kwargs)
            raw_usage = getattr(response, "usage", None)
            total_input += raw_usage.prompt_tokens if raw_usage else 0
            total_output += raw_usage.completion_tokens if raw_usage else 0

        return AIResponse(
            content=response.choices[0].message.content or "",
            usage=AIUsage(
                input_tokens=total_input,
                output_tokens=total_output,
                total_tokens=total_input + total_output,
            ),
        )
