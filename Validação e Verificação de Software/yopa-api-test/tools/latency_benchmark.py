#!/usr/bin/env python3
"""
Pipeline latency benchmark.
Measures sanitize_pii + preprocess_message (spellcheck) overhead and full AI
response time across 5 scenarios, from optimal to worst.

Usage:
    python tools/latency_benchmark.py [--iterations N] [--real-ai]

    --iterations N   Timed runs per scenario (default: 5). First run is warm-up.
    --real-ai        Use actual LiteLLM call. Requires AI_API_KEY + AI_MODEL in .env.
                     Without this flag, the AI phase is skipped and marked as [mock].
"""
from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── env defaults before src imports ───────────────────────────────────────────
os.environ.setdefault("STORAGE_TYPE", "local")
os.environ.setdefault("DATA_PATH", str(ROOT / "data"))
os.environ.setdefault("REDIS_URL", "redis://localhost:6379")
os.environ.setdefault("SESSION_TTL", "86400")
os.environ.setdefault("ANALYZER_LANGUAGES", '["en", "pt"]')
os.environ.setdefault("MAX_TOOL_ROUNDS", "5")
os.environ.setdefault("AUTH_MODE", "standalone")
os.environ.setdefault("INTERNAL_TOKEN", "")

from src.infrastructure.security import sanitize_pii       # noqa: E402
from src.infrastructure.nlp.analyzer import preprocess_message  # noqa: E402
from src.domain.conversation import HistoryMessage         # noqa: E402


# ── Scenario definitions ───────────────────────────────────────────────────────

def _history(n: int) -> list[HistoryMessage]:
    msgs = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        msgs.append(HistoryMessage(
            message_id=str(uuid.uuid4()),
            session_id="bench",
            role=role,
            content=f"Mensagem de histórico número {i + 1}.",
            timestamp="2024-01-01T00:00:00Z",
            status="delivered",
        ))
    return msgs


SCENARIOS = [
    {
        "label": "1 — Ótimo",
        "description": "Mensagem curta, limpa, sem PII, sem histórico",
        "message": "Olá! Pode me explicar como funciona o sistema?",
        "history": _history(0),
    },
    {
        "label": "2 — Bom",
        "description": "Mensagem média, sem PII, histórico pequeno (5 msgs)",
        "message": (
            "Preciso de ajuda para configurar minha conta no sistema. "
            "Quais são os passos necessários para ativar as notificações "
            "e personalizar o painel principal?"
        ),
        "history": _history(5),
    },
    {
        "label": "3 — Médio",
        "description": "Mensagem média com erros ortográficos, 1 PII (e-mail), histórico moderado (10 msgs)",
        "message": (
            "Oi, estou tentano fazer lgoin no ssitema mas nao consgo. "
            "Meu emial é usuario@empresa.com.br e a senah nao funciona. "
            "Já tentei redefinr a sennha duas vezes mas o lnik nao chegou. "
            "Pode me ajdudar com isso? É urgente pq preciso acessar hoje."
        ),
        "history": _history(10),
    },
    {
        "label": "4 — Ruim",
        "description": "Mensagem longa com erros, 3 PIIs (e-mail, telefone, nome), histórico longo (20 msgs)",
        "message": (
            "Bom dia. Meu nome é João Silva e estou com um problema sério. "
            "Já tentei contactar o suporte pelo telefoone (11) 98765-4321 mas "
            "ninguem atende. Meu emial é joao.silva@gmail.com e precisso de "
            "ajuda com urgencia. O sistema esta apresentndo erros na hora de "
            "procesar meus pedidos. Quando clcio em confirmar aparece mensagem "
            "de erro 500. Isso esta acontecnedo desde ontem e já perdi três "
            "pedidos importants. Minha equipe interia esta bloqueada e nao "
            "consguimos trabalhar. Já tentatei limppar o cache, trocar de "
            "navgador e nada resolveu. Por favor me ajudem o mais rápido "
            "possivel porque estou perdendo dinheiro a cada hora."
        ),
        "history": _history(20),
    },
    {
        "label": "5 — Péssimo",
        "description": "Mensagem muito longa com muitos erros e 5 PIIs, histórico máximo (40 msgs)",
        "message": (
            "Olá. Meu nome é Maria Aparecida dos Santos, CPF 123.456.789-00, "
            "e preciso reportar um problema critico no sistema. Pode contatr pelo "
            "emial maria.santos@empresa.com.br ou pelo telefoone (21) 99887-6543. "
            "O endereço da empresa é Rua das Flores 123, São Paulo, SP. "
            "O problema começou na semana passda quando atualizarams o sistama. "
            "Agora todos os relatorios geraados estao com os calculos erraados. "
            "Verifiquei com o controler financeiro e ele confirmouu que os numeros "
            "nao batem com os do mês anteroir. Já tentatei regerar os relatorios "
            "tres vezes e sempree aparece o mesmo eroo. Nossa equipe de contabilidde "
            "esta bloqueadda e nao consigue fechar o balanço mensal. O diretor "
            "financeiro esta muito preocupaado pois temos uma audtoria semana que "
            "vem. Já tentei entrar em contatoo com o suporte tecnico pelo chat, "
            "pelo emial suporte@sistema.com e pelo telefoone de emergencia mas "
            "ninguem responddeu. Preciso de uma solucao urgente. Isso esta afetanddo "
            "toda a operacao da empressa. Temos 50 funcionariso dependenttes desse "
            "sistama para trabalhar. Cada hora de indisponibildade representa um "
            "prejuizo significatvo para o negocio. Por favor escalem esse chamaddo "
            "para o nivel mais alto possivel e me contatattem assim que tiverem "
            "qualquer atualizacaoo sobre o andamento da resolucaoo do problema."
        ),
        "history": _history(40),
    },
]


# ── Timing helpers ─────────────────────────────────────────────────────────────

class PhaseResult:
    def __init__(self):
        self.pii_ms: list[float] = []
        self.spell_ms: list[float] = []
        self.ai_ms: list[float] = []

    def add(self, pii: float, spell: float, ai: float):
        self.pii_ms.append(pii)
        self.spell_ms.append(spell)
        self.ai_ms.append(ai)

    def _stats(self, values: list[float]) -> tuple[float, float, float]:
        if not values:
            return 0.0, 0.0, 0.0
        mean = statistics.mean(values)
        p95 = sorted(values)[int(len(values) * 0.95)] if len(values) > 1 else values[0]
        peak = max(values)
        return mean, p95, peak

    @property
    def pii(self):    return self._stats(self.pii_ms)
    @property
    def spell(self):  return self._stats(self.spell_ms)
    @property
    def ai(self):     return self._stats(self.ai_ms)

    @property
    def total_ms(self) -> list[float]:
        return [p + s + a for p, s, a in zip(self.pii_ms, self.spell_ms, self.ai_ms)]

    @property
    def total(self):  return self._stats(self.total_ms)

    @property
    def preprocessing_ms(self) -> list[float]:
        return [p + s for p, s in zip(self.pii_ms, self.spell_ms)]

    @property
    def preprocessing(self): return self._stats(self.preprocessing_ms)


def _time_preprocessing(message: str) -> tuple[float, float, str]:
    t0 = time.perf_counter()
    sanitized = sanitize_pii(message)
    t_pii = (time.perf_counter() - t0) * 1000

    t0 = time.perf_counter()
    _ = preprocess_message(sanitized)
    t_spell = (time.perf_counter() - t0) * 1000

    return t_pii, t_spell, sanitized


def _time_ai(message: str, history: list[HistoryMessage], system: str) -> float:
    from src.infrastructure.ai.client import AIClient
    from src.domain.conversation import HistoryMessage as HM

    user_msg = HM(
        message_id=str(uuid.uuid4()), session_id="bench",
        role="user", content=message,
        timestamp="2024-01-01T00:00:00Z", status="delivered",
    )
    client = AIClient()
    t0 = time.perf_counter()
    client.complete(system=system, messages=history + [user_msg])
    return (time.perf_counter() - t0) * 1000


# ── Runner ─────────────────────────────────────────────────────────────────────

def run_scenario(scenario: dict, iterations: int, real_ai: bool) -> PhaseResult:
    result = PhaseResult()
    system = "Você é um assistente prestativo e direto."
    total_runs = iterations + 1  # +1 warm-up

    for run in range(total_runs):
        warm_up = run == 0
        t_pii, t_spell, sanitized = _time_preprocessing(scenario["message"])
        t_ai = 0.0
        if real_ai:
            t_ai = _time_ai(sanitized, scenario["history"], system)
        if not warm_up:
            result.add(t_pii, t_spell, t_ai)

    return result


# ── Output ─────────────────────────────────────────────────────────────────────

def _fmt(mean: float, p95: float, peak: float) -> str:
    return f"{mean:6.1f} / {p95:6.1f} / {peak:6.1f}"


def print_report(results: list[tuple[dict, PhaseResult]], real_ai: bool, iterations: int):
    ai_label = "AI (real)" if real_ai else "AI (skip)"
    w_case = 22
    w_phase = 24

    sep = "─" * (w_case + 3 * (w_phase + 3) + 2)
    header_phase = f"{'mean':>6} / {'p95':>6} / {'peak':>6} ms"

    print()
    print(f"  Latency Benchmark  —  {iterations} timed runs per scenario  (1 warm-up excluded)")
    print(f"  {'Presidio' if real_ai else 'sanitize_pii'} model: pt_core_news_sm  |  Spellcheck: pyspellchecker  |  AI: {'LiteLLM' if real_ai else 'not measured'}")
    print()
    print(f"  {'Scenario':<{w_case}}  {'sanitize_pii':<{w_phase}}  {'preprocess (spell)':<{w_phase}}  {'Preprocessing total':<{w_phase}}")
    print(f"  {'':<{w_case}}  {header_phase}  {header_phase}  {header_phase}")
    print(f"  {sep}")

    for scenario, res in results:
        pii_s = _fmt(*res.pii)
        spell_s = _fmt(*res.spell)
        pre_s = _fmt(*res.preprocessing)
        label = scenario["label"]
        print(f"  {label:<{w_case}}  {pii_s}  {spell_s}  {pre_s}")

    if real_ai:
        print()
        print(f"  {'Scenario':<{w_case}}  {'sanitize_pii':<{w_phase}}  {'preprocess (spell)':<{w_phase}}  {'AI call':<{w_phase}}  {'Total':<{w_phase}}")
        print(f"  {'':<{w_case}}  {header_phase}  {header_phase}  {header_phase}  {header_phase}")
        print(f"  {sep}{'─' * (w_phase + 3)}")
        for scenario, res in results:
            pii_s = _fmt(*res.pii)
            spell_s = _fmt(*res.spell)
            ai_s = _fmt(*res.ai)
            total_s = _fmt(*res.total)
            label = scenario["label"]
            print(f"  {label:<{w_case}}  {pii_s}  {spell_s}  {ai_s}  {total_s}")

    print()
    print("  Notes:")
    print("  · Values: mean / p95 / peak  (milliseconds, wall clock, single process)")
    print("  · First call per process includes model load (warm-up excluded from stats)")
    if not real_ai:
        print("  · AI phase not measured — run with --real-ai to include LiteLLM call time")
    print()


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--iterations", type=int, default=5, metavar="N",
                        help="Timed runs per scenario, excluding warm-up (default: 5)")
    parser.add_argument("--real-ai", action="store_true",
                        help="Make actual LiteLLM calls (requires AI_API_KEY + AI_MODEL in .env or env vars)")
    args = parser.parse_args()

    if args.real_ai:
        from dotenv import load_dotenv
        load_dotenv(ROOT / ".env")
        from src.infrastructure.config import settings
        if not settings.AI_API_KEY or not settings.AI_MODEL:
            print("ERROR: --real-ai requires AI_API_KEY and AI_MODEL to be set in .env", file=sys.stderr)
            sys.exit(1)
        print(f"\n  Using model: {settings.AI_MODEL}")

    print(f"\n  Running {len(SCENARIOS)} scenarios × {args.iterations + 1} runs (1 warm-up) ...")

    results: list[tuple[dict, PhaseResult]] = []
    for i, scenario in enumerate(SCENARIOS, 1):
        print(f"  [{i}/{len(SCENARIOS)}] {scenario['label']} — {scenario['description']}", end="", flush=True)
        res = run_scenario(scenario, args.iterations, args.real_ai)
        pre_mean = statistics.mean(res.preprocessing_ms)
        print(f"  → preprocessing avg {pre_mean:.0f} ms")
        results.append((scenario, res))

    print_report(results, args.real_ai, args.iterations)


if __name__ == "__main__":
    main()
