"""
Builds the agent system prompt from AgentContextBase.
Called on POST /agent and PUT /agent/context. The result is cached in Redis
and injected into every model call via chat_service.
escalation_trigger is backend logic — it never appears in the system prompt.
"""
from src.domain.agent import AgentContextBase


def build_system_prompt(context: AgentContextBase) -> str:
    parts: list[str] = []

    parts.append(context.persona if context.persona else "You are a virtual assistant.")

    meta: list[str] = []
    if context.tone:
        meta.append(f"- Tone: {context.tone}")
    if context.language:
        meta.append(f"- Language: {context.language}")
    if context.segment:
        meta.append(f"- Audience segment: {context.segment}")
    if meta:
        parts.append("## Settings\n" + "\n".join(meta))

    if context.behavior:
        parts.append(f"## Behavior\n{context.behavior}")

    has_topics = bool(context.restrictions and context.restrictions.topics)
    has_files  = bool(context.restrictions and context.restrictions.files)

    if has_topics or has_files:
        block_lines: list[str] = ["## Restrictions"]
        if has_topics:
            topics = "\n".join(f"- {t}" for t in context.restrictions.topics)
            block_lines.append(f"You are FORBIDDEN from responding about the following topics:\n{topics}")
        if has_files:
            files = "\n".join(f"- {f.name}" for f in context.restrictions.files)
            block_lines.append(
                f"You must NEVER share, mention, or provide access to the following files or documents:\n{files}"
            )
        block = "\n\n".join(block_lines)
        if context.fallback_message:
            block += (
                f'\n\nWhen the user asks about a restricted topic or file, respond EXACTLY with:\n'
                f'"{context.fallback_message}"'
            )
        parts.append(block)
    elif context.fallback_message:
        parts.append(
            f'## Default response\nWhen you cannot answer or the topic is out of scope, '
            f'use exactly:\n"{context.fallback_message}"'
        )

    return "\n\n".join(parts)
