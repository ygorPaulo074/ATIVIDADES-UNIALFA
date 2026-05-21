"""
Parte 1 — Módulo: src/application/context_builder.py

ESCOPO
------
build_system_prompt(AgentContextBase) -> str

Constrói o prompt de sistema enviado à IA a partir do contexto do agente.
É uma função pura de transformação: mesmo input → mesmo output.

REGRAS QUE PRECISAM SER VALIDADAS
---------------------------------
1. Inclui (quando definidos): persona, tone, language, segment, behavior,
   restrictions.topics, restrictions.files, fallback_message
2. NUNCA inclui: escalation_trigger (lógica de backend pura)
3. NUNCA inclui: knowledge_base (só é usada via tool use)

TIPOS DE TESTE
--------------
- unit         : todos os testes
- regression   : escalation_trigger e knowledge_base não podem vazar
"""
import pytest

from tests.shared.log_helper import logged

from src.application.context_builder import build_system_prompt
from src.domain.agent import (
    AgentContextBase,
    RestrictionsConfig,
    KnowledgeBaseConfig,
    EscalationTrigger,
    EscalationCondition,
    FileReference,
)


@pytest.mark.unit
@pytest.mark.part1
class TestBuildSystemPromptIncludesFields:
    """Valida que cada campo do contexto aparece no prompt quando definido."""

    @logged
    def test_minimal_context_produces_default_persona(self):
        """Sem persona, usa o fallback 'You are a virtual assistant.'"""
        ctx = AgentContextBase()
        prompt = build_system_prompt(ctx)
        assert "You are a virtual assistant." in prompt

    @logged
    def test_persona_replaces_default(self):
        ctx = AgentContextBase(persona="Você é um assistente jurídico.")
        prompt = build_system_prompt(ctx)
        assert "Você é um assistente jurídico." in prompt
        assert "You are a virtual assistant." not in prompt

    @logged
    def test_tone_appears_in_settings_section(self):
        ctx = AgentContextBase(tone="formal")
        prompt = build_system_prompt(ctx)
        assert "## Settings" in prompt
        assert "Tone: formal" in prompt

    @logged
    def test_language_appears_in_settings_section(self):
        ctx = AgentContextBase(language="pt")
        prompt = build_system_prompt(ctx)
        assert "Language: pt" in prompt

    @logged
    def test_segment_appears_in_settings_section(self):
        ctx = AgentContextBase(segment="varejo")
        prompt = build_system_prompt(ctx)
        assert "Audience segment: varejo" in prompt

    @logged
    def test_behavior_appears_in_its_own_section(self):
        ctx = AgentContextBase(behavior="Seja sempre cordial.")
        prompt = build_system_prompt(ctx)
        assert "## Behavior" in prompt
        assert "Seja sempre cordial." in prompt

    @logged
    def test_restrictions_topics_appear(self):
        ctx = AgentContextBase(
            restrictions=RestrictionsConfig(topics=["politica", "religiao"]),
        )
        prompt = build_system_prompt(ctx)
        assert "## Restrictions" in prompt
        assert "politica" in prompt
        assert "religiao" in prompt
        assert "FORBIDDEN" in prompt

    @logged
    def test_restrictions_files_appear(self):
        ctx = AgentContextBase(
            restrictions=RestrictionsConfig(
                files=[FileReference(name="senha.txt", url="http://x/senha.txt")]
            ),
        )
        prompt = build_system_prompt(ctx)
        assert "senha.txt" in prompt
        assert "NEVER share" in prompt

    @logged
    def test_fallback_message_in_restrictions_when_restrictions_present(self):
        """Com restrictions, o fallback é incluído dentro da seção Restrictions."""
        ctx = AgentContextBase(
            restrictions=RestrictionsConfig(topics=["X"]),
            fallback_message="Não posso responder isso.",
        )
        prompt = build_system_prompt(ctx)
        assert "## Restrictions" in prompt
        assert "Não posso responder isso." in prompt

    @logged
    def test_fallback_message_as_default_response_without_restrictions(self):
        """Sem restrictions, fallback vira seção '## Default response'."""
        ctx = AgentContextBase(fallback_message="Não sei responder.")
        prompt = build_system_prompt(ctx)
        assert "## Default response" in prompt
        assert "Não sei responder." in prompt


@pytest.mark.unit
@pytest.mark.regression
@pytest.mark.part1
class TestBuildSystemPromptExclusions:
    """
    Regras de exclusão — protegem contra vazamento de lógica de backend
    para a IA. Qualquer mudança acidental em build_system_prompt que
    incluísse esses campos quebraria esses testes.
    """

    @logged
    def test_escalation_trigger_never_included(self):
        """escalation_trigger NUNCA pode aparecer no prompt."""
        trigger = EscalationTrigger(
            operator="OR",
            conditions=[
                EscalationCondition(type="keyword", values=["humano", "atendente"]),
            ],
        )
        ctx = AgentContextBase(
            persona="Assistente",
            escalation_trigger=trigger,
        )
        prompt = build_system_prompt(ctx)
        assert "humano" not in prompt
        assert "atendente" not in prompt
        assert "escalation" not in prompt.lower()

    @logged
    def test_knowledge_base_never_included(self):
        """knowledge_base NUNCA pode aparecer no prompt (só via tool use)."""
        kb = KnowledgeBaseConfig(
            urls=["https://docs.example.com/manual"],
            files=[FileReference(name="catalogo.pdf", url="https://x/catalogo.pdf")],
        )
        ctx = AgentContextBase(persona="Assistente", knowledge_base=kb)
        prompt = build_system_prompt(ctx)
        assert "docs.example.com" not in prompt
        assert "catalogo.pdf" not in prompt
        assert "knowledge" not in prompt.lower()


@pytest.mark.unit
@pytest.mark.part1
class TestBuildSystemPromptDeterminism:
    """Função pura — mesmo input gera mesma saída sempre."""

    @logged
    def test_same_input_produces_same_output(self):
        ctx = AgentContextBase(persona="X", tone="formal", language="pt")
        assert build_system_prompt(ctx) == build_system_prompt(ctx)
