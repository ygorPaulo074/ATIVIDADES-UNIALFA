# 00 — Decisões de Modelagem e Arquitetura

> Registro das decisões tomadas ao longo do projeto.
> Atualizado em junho/2026 após conclusão das fases 1 e 2.

## Princípios gerais

| Tema | Decisão |
|---|---|
| **Persistência** | PostgreSQL. O frontend não usa `localStorage` para dados financeiros. |
| **Normalização** | Modelo Nexus Finance: `categories`, `payment_methods`, etc. são tabelas. |
| **IDs** | Serial no banco — o frontend nunca gera IDs (`Date.now()` eliminado). |
| **Arquitetura** | SQL explícito, sem ORM. Lógica de negócio em PL/pgSQL; FastAPI é camada fina. |
| **PATCH dinâmico** | Backend usa allowlist por tabela (`_ALLOWED_PATCH`) — só campos permitidos são atualizados. |

## Autenticação (multiusuário)

- Tabela `users`: `username`, `email`, `password_hash` (bcrypt).
- Login por username ou email + senha.
- Sessão: token opaco em `sessions` (TTL 30 dias, deslizante).
- `seed_default_categories()` chamada no cadastro — cria 16 categorias padrão.
- Isolamento por usuário: `user_id` em todas as tabelas de dados.

## Modelo financeiro

### Competência × Caixa
- **`bills`** = regime de competência: obrigações/direitos futuros com `due_date` e `status`.
- **`transactions`** = regime de caixa: movimentações efetivadas. Quitar uma bill via `pay_bill()` gera uma transaction vinculada.
- **`wallets`**: onde o dinheiro fica. Saldo calculado por `wallet_balance()` no banco.

### Status de bills (derivado, nunca armazenado)
A função `bill_status(bill_id)` calcula o status em tempo real:
- `cancelada` — `cancelled_at IS NOT NULL`
- `quitada` — `SUM(transactions.amount) >= bill.amount`
- `parcial` — pagamento parcial
- `atrasada` — `due_date < CURRENT_DATE` e sem pagamento
- `a_vencer` — default

### Recorrências
- Tabela `recurrences` com regras: frequência (`weekly`/`monthly`/`yearly`), `interval_count`, `reference_day`, `start_date`, fim (por data ou nº de ocorrências).
- `recurrence_dates()` — função set-returning, virtual (não grava).
- `generate_recurrence_occurrences()` — materializa em bills até uma data.
- `cash_flow()` inclui recorrências com `materialize=false` diretamente (sem duplicar).

### Parcelamento
- `installment_plans` (pai) → `generate_installments()` cria N bills-filhas.
- Última parcela absorve arredondamento.

### Fluxo de caixa
- `cash_flow(user_id, start, end, granularity)` — função SQL que combina:
  - Realizado: `transactions` settled no período.
  - Projetado: `bills` a_vencer + recorrências não materializadas.
- Granularidade: `daily`, `weekly`, `monthly`.
- Frontend consome via `GET /cash-flow` na aba "Fluxo de Caixa".

### Formas de pagamento × Tags
- **`payment_methods`**: lista fixa global (seeds em `db/seeds/01_payment_methods.sql`).
- **`tags`**: criadas pelo usuário, limite de 5 por usuário (trigger `trg_tags_limit`). N:N com transações.

## Investimentos
- `investments` + `contributions` (histórico) + `value_history` (série temporal).
- Métricas via funções SQL: `invested_total()`, `position_value()`, `investment_return()`.
- `record_market_value()` — upsert de cotação (manual ou via brapi sync).
- `track_brapi=true` → `POST /investments/sync-brapi` busca preços do dia na brapi.dev.

## Camada de IA (efêmera — Redis)
- Chats, mensagens e extratos em **Redis** com **TTL de 24 horas**.
- Frontend exibe aviso: conversa expira em 24h.
- IATab simplificada: analisa dados da API, não persiste lançamentos via chat (fluxo de aprovação removido).

## Endpoints adicionados na Fase 1 (junho/2026)

| Endpoint | Descrição |
|---|---|
| `DELETE /recurrences/{rid}` | Deletar recorrência |
| `DELETE /installment-plans/{pid}` | Deletar plano de parcelamento |
| `PATCH /wallets/{wid}` | Editar carteira |
| `PATCH /categories/{cid}` | Editar categoria |
| `PATCH /bills/{bid}` | Editar bill (campos financeiros) |
| `PATCH /transactions/{tid}` | Editar transação |
| `PATCH /investments/{iid}` | Editar investimento |
| `POST /recurrences/{rid}/toggle` | Ativar/desativar recorrência |
| `GET /investments/{iid}/contributions` | Listar aportes/retiradas |

## Migração frontend → API (Fase 2, junho/2026)

```
localStorage (Fase 0)
    ↓
API REST (Fase 2)
```

- App.tsx carrega wallets, categories, payment-methods e dados financeiros via API no mount.
- `onRefresh()` recarrega tudo após cada mutação.
- Tabs recebem dados e recursos como props — sem estado local de dados financeiros.
- `storage.ts` e `constants/finance.ts` mantidos mas não usados pelas tabs principais.
