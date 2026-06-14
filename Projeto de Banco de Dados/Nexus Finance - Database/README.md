# FinanControl — Controle Financeiro com IA

Sistema de gestão financeira pessoal com PostgreSQL, FastAPI (Python) e React (TypeScript).

```
projeto-banco-de-dados/
├── frontend/   React + Vite + TypeScript        (porta 5173)
├── backend/    FastAPI + Groq (Llama 3.3)       (porta 8000)
├── db/         PostgreSQL + PL/pgSQL             (porta 5432)
├── redis/      IA efêmera (TTL 24h)              (porta 6379)
├── docs/       Análise, decisões e divergências
└── docker-compose.yml
```

---

## Sumário

1. [Arquitetura](#arquitetura)
2. [Setup rápido](#setup-rápido)
3. [Banco de Dados — Documentação Completa](#banco-de-dados--documentação-completa)
   - [Tipos (ENUMs)](#tipos-enums)
   - [Diagrama ER Textual](#diagrama-er-textual)
   - [Tabelas](#tabelas)
   - [Funções SQL](#funções-sql)
   - [Triggers](#triggers)
   - [Seeds](#seeds)
   - [Índices](#índices)
   - [Fluxos principais](#fluxos-principais)
4. [Backend (FastAPI)](#backend-fastapi)
5. [Frontend (React)](#frontend-react)

---

## Arquitetura

```
┌────────────┐   HTTP/JSON   ┌─────────────────┐   psycopg3   ┌──────────────┐
│  Frontend  │ ────────────► │  FastAPI Backend │ ───────────► │  PostgreSQL  │
│  (React)   │               │  (Python 3.12)  │              │  (schema.sql)│
└────────────┘               └─────────────────┘              └──────────────┘
                                      │                               ▲
                                      │ redis-py                      │
                                      ▼                        16 funções PL/pgSQL
                               ┌────────────┐                 + 3 triggers
                               │   Redis    │
                               │ (IA/chats) │
                               └────────────┘
```

**Princípio central:** toda lógica financeira fica no banco (PL/pgSQL). FastAPI é camada fina de autenticação + autorização. Frontend nunca gera IDs nem calcula saldos — esses valores vêm sempre do banco.

---

## Setup rápido

### Stack completa (Docker)

```bash
# 1. Copiar variáveis de ambiente
cp backend/.env.example backend/.env   # preencher as chaves abaixo
cp .env.example .env                   # credenciais do Postgres (opcional)

# 2. Subir tudo
docker compose up --build

# Acesso:
# Frontend:  http://localhost:5173
# Backend:   http://localhost:8000
# Postgres:  localhost:5432
# Redis:     localhost:6379
```

Para parar: `Ctrl+C`  
Para destruir volumes (recriar schema do zero): `docker compose down -v`

### Desenvolvimento local (sem Docker)

```bash
# Banco + Redis
docker compose up db redis -d

# Backend
cd backend
cp .env.example .env   # preencher variáveis
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Variáveis de ambiente do backend (`backend/.env`)

| Variável | Descrição | Exemplo |
|---|---|---|
| `DATABASE_URL` | DSN PostgreSQL | `postgresql://user:pass@localhost:5432/finapp` |
| `GROQ_API_KEY` | Chave Groq (LLM de IA) | `gsk_...` |
| `BRAPI_TOKEN` | Token brapi.dev (cotações) | `abc123` |
| `REDIS_URL` | DSN Redis (chats IA) | `redis://localhost:6379` |

---

## Banco de Dados — Documentação Completa

**Arquivo principal:** `db/schema.sql`  
**Funções:** `db/functions/01_*.sql` … `16_*.sql`  
**Seeds:** `db/seeds/`

---

### Tipos (ENUMs)

| Tipo | Valores | Usado em |
|---|---|---|
| `bill_type` | `payable`, `receivable` | `bills`, `recurrences` |
| `transaction_type` | `inflow`, `outflow` | `transactions` |
| `transaction_status` | `settled`, `reversed` | `transactions` |
| `category_type` | `income`, `expense` | `categories` |
| `frequency` | `weekly`, `monthly`, `yearly` | `recurrences` |
| `contribution_type` | `deposit`, `withdrawal` | `contributions` |
| `investment_type` | `stock`, `reit`, `etf`, `bdr`, `crypto`, `treasury`, `fixed_income` | `investments` |

---

### Diagrama ER Textual

```
users ──┬── wallets
        ├── categories
        ├── tags ──────────────── transaction_tags ── transactions
        ├── installment_plans ──► bills
        ├── recurrences ────────► bills
        ├── bills ──────────────► transactions (via pay_bill)
        ├── transactions
        └── investments ──┬── contributions
                          └── value_history

payment_methods ──── bills
                └─── transactions
```

**Regras de integridade chave:**
- `bills.cancelled_at` é o único campo de status gravado; o resto é calculado por `bill_status()`.
- `installment_number` exige `installment_plan_id IS NOT NULL` (constraint `bill_installment_coherent`).
- `recurrences`: `end_date` e `occurrences_count` são mutuamente exclusivos (constraint `recurrence_end_exclusive`).
- `tags`: máximo 5 por usuário — enforçado por trigger `tags_limit`.

---

### Tabelas

#### `users`
Usuários do sistema.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | Chave primária |
| `username` | `VARCHAR(50)` | NOT NULL, UNIQUE | Nome de usuário |
| `email` | `VARCHAR(255)` | UNIQUE, nullable | Email (opcional) |
| `password_hash` | `TEXT` | NOT NULL | Hash bcrypt da senha |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | Data de criação |

---

#### `sessions`
Sessões de autenticação (token opaco, TTL 30 dias deslizante).

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users ON DELETE CASCADE | Dono da sessão |
| `token` | `TEXT` | NOT NULL, UNIQUE | Token urlsafe(32) |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |
| `expires_at` | `TIMESTAMPTZ` | NOT NULL | Prorrogado em cada uso |

---

#### `payment_methods`
Formas de pagamento — lista fixa global (sem `user_id`).

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | `SMALLSERIAL` | PK |
| `name` | `VARCHAR(40)` | Ex: PIX, Cartão Crédito, Boleto |

> Populada em `db/seeds/01_payment_methods.sql`. Nunca deletada por usuário (ON DELETE RESTRICT nas FKs).

---

#### `wallets`
Carteiras / contas bancárias do usuário.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `name` | `VARCHAR(100)` | NOT NULL | Nome da carteira |
| `initial_balance` | `NUMERIC(14,2)` | DEFAULT 0 | Saldo inicial |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |

> Saldo atual = `initial_balance + Σ transactions settled`. Calculado por `wallet_balance(id)` — campo `balance` na API.

---

#### `categories`
Categorias por usuário (income ou expense).

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `name` | `VARCHAR(60)` | NOT NULL | Nome |
| `type` | `category_type` | NOT NULL | `income` ou `expense` |
| — | — | UNIQUE(user_id, name, type) | Sem duplicatas por usuário |

> Semeadas automaticamente via `seed_default_categories()` no cadastro: 10 despesa + 6 receita.  
> Trigger `trg_tx_type_coherence` impede vincular categoria de tipo errado a uma transação.  
> Trigger `trg_bill_type_coherence` faz o mesmo para bills.

---

#### `tags`
Etiquetas livres do usuário (máx. 5). Relação N:N com transações via `transaction_tags`.

| Coluna | Tipo | Restrições |
|---|---|---|
| `id` | `BIGSERIAL` | PK |
| `user_id` | `BIGINT` | FK → users CASCADE |
| `name` | `VARCHAR(30)` | NOT NULL, UNIQUE(user_id, name) |

> Trigger `tags_limit` rejeita INSERT quando o usuário já tem 5 tags.

---

#### `installment_plans`
Compras parceladas — registro pai que gera N bills.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `description` | `VARCHAR(120)` | NOT NULL | Ex: "Notebook Samsung" |
| `total_amount` | `NUMERIC(14,2)` | CHECK > 0 | Valor total da compra |
| `total_installments` | `INT` | CHECK > 0 | Nº de parcelas |
| `category_id` | `BIGINT` | FK → categories SET NULL | — |
| `payment_method_id` | `SMALLINT` | FK → payment_methods RESTRICT | — |
| `purchase_date` | `DATE` | NOT NULL | Data da compra (base para vencimentos) |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |

> Ao criar, `generate_installments(plan_id)` é chamado — cria as bills filhas automaticamente.

---

#### `recurrences`
Regras de recorrência (a regra, não as ocorrências).

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `type` | `bill_type` | NOT NULL | `payable` ou `receivable` |
| `description` | `VARCHAR(120)` | NOT NULL | — |
| `amount` | `NUMERIC(14,2)` | CHECK > 0 | — |
| `category_id` | `BIGINT` | FK SET NULL | — |
| `payment_method_id` | `SMALLINT` | FK RESTRICT | — |
| `frequency` | `frequency` | NOT NULL | `weekly`, `monthly` ou `yearly` |
| `interval_count` | `INT` | DEFAULT 1, CHECK > 0 | Ex: 2 = "a cada 2 meses" |
| `reference_day` | `INT` | CHECK 1–31 | Dia do mês de referência |
| `start_date` | `DATE` | NOT NULL | Primeira ocorrência |
| `end_date` | `DATE` | nullable | Fim por data (exclusivo com `occurrences_count`) |
| `occurrences_count` | `INT` | nullable | Fim por contagem (exclusivo com `end_date`) |
| `materialize` | `BOOLEAN` | DEFAULT true | `true` = gera bills; `false` = só projeção no cash_flow |
| `active` | `BOOLEAN` | DEFAULT true | Toggle via `POST /recurrences/{id}/toggle` |

---

#### `bills`
Obrigações financeiras (regime de competência). Status **derivado**, nunca armazenado.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `type` | `bill_type` | NOT NULL | `payable` ou `receivable` |
| `description` | `VARCHAR(120)` | NOT NULL | — |
| `amount` | `NUMERIC(14,2)` | CHECK > 0 | Valor total da obrigação |
| `due_date` | `DATE` | NOT NULL | Vencimento |
| `counterparty` | `VARCHAR(120)` | nullable | Credor ou devedor |
| `category_id` | `BIGINT` | FK SET NULL | — |
| `payment_method_id` | `SMALLINT` | FK RESTRICT | — |
| `recurrence_id` | `BIGINT` | FK → recurrences SET NULL | Vínculo à regra de origem |
| `installment_plan_id` | `BIGINT` | FK → installment_plans CASCADE | Plano pai |
| `installment_number` | `INT` | nullable | Nº da parcela (1, 2, …N) |
| `cancelled_at` | `TIMESTAMPTZ` | nullable | Único status gravado manualmente |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |

**Status calculado por `bill_status(id)` — nunca gravado:**

| Status | Condição |
|---|---|
| `cancelada` | `cancelled_at IS NOT NULL` |
| `quitada` | `Σ transactions.amount >= bill.amount` (settled) |
| `parcial` | Pagamento parcial |
| `atrasada` | `due_date < CURRENT_DATE` e sem pagamento |
| `a_vencer` | Default (data futura, sem pagamento) |

---

#### `transactions`
Movimentações efetivas (regime de caixa).

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `wallet_id` | `BIGINT` | FK → wallets CASCADE | Carteira debitada/creditada |
| `type` | `transaction_type` | NOT NULL | `inflow` ou `outflow` |
| `description` | `VARCHAR(120)` | NOT NULL | — |
| `amount` | `NUMERIC(14,2)` | CHECK > 0 | — |
| `date` | `DATE` | NOT NULL | Data efetiva |
| `category_id` | `BIGINT` | FK SET NULL | — |
| `payment_method_id` | `SMALLINT` | FK RESTRICT | — |
| `bill_id` | `BIGINT` | FK → bills SET NULL | Vínculo à bill quitada |
| `status` | `transaction_status` | DEFAULT `settled` | `settled` ou `reversed` |
| `notes` | `TEXT` | nullable | Observações livres |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |

---

#### `transaction_tags`
Junção N:N entre transações e tags.

| Coluna | Tipo |
|---|---|
| `transaction_id` | FK → transactions CASCADE |
| `tag_id` | FK → tags CASCADE |

---

#### `investments`
Posições de investimento.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `user_id` | `BIGINT` | FK → users CASCADE | — |
| `symbol` | `VARCHAR(60)` | NOT NULL | Ticker (PETR4, MXRF11, BTC…) |
| `type` | `investment_type` | NOT NULL | Enum de tipo |
| `quantity` | `NUMERIC(18,8)` | CHECK >= 0 | Suporta frações (cripto) |
| `currency` | `CHAR(3)` | DEFAULT 'BRL' | Moeda do ativo |
| `track_brapi` | `BOOLEAN` | DEFAULT false | Sincronizar via brapi.dev? |
| `purchase_date` | `DATE` | NOT NULL | Data de compra |
| `maturity_date` | `DATE` | nullable | Vencimento (renda fixa) |
| `notes` | `TEXT` | nullable | — |
| `created_at` | `TIMESTAMPTZ` | DEFAULT now() | — |

---

#### `contributions`
Histórico de aportes e retiradas por investimento.

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `investment_id` | `BIGINT` | FK → investments CASCADE | — |
| `type` | `contribution_type` | NOT NULL | `deposit` ou `withdrawal` |
| `amount` | `NUMERIC(14,2)` | CHECK > 0 | — |
| `date` | `DATE` | NOT NULL | — |
| `notes` | `TEXT` | nullable | — |

---

#### `value_history`
Série temporal do preço unitário (cotação diária).

| Coluna | Tipo | Restrições | Descrição |
|---|---|---|---|
| `id` | `BIGSERIAL` | PK | — |
| `investment_id` | `BIGINT` | FK → investments CASCADE | — |
| `date` | `DATE` | NOT NULL | Data da cotação |
| `market_value` | `NUMERIC(18,8)` | CHECK > 0 | Preço unitário no dia |
| — | — | UNIQUE(investment_id, date) | Um registro por ativo por dia |

> Populada por `record_market_value()` — manual ou via sync brapi.

---

### Funções SQL

Todas em `db/functions/`. Organizadas em ordem de dependência.

---

#### `clamp_day(p_month_start DATE, p_day INT) → DATE`
**Arquivo:** `01_clamp_day.sql` | **Volatilidade:** IMMUTABLE

Ajusta um dia ao mês — se `p_day=31` e o mês tem 28 dias, retorna o último dia do mês. Evita datas inválidas como 30 de fevereiro.

```sql
SELECT clamp_day('2024-02-01', 31);
-- Retorna: 2024-02-29
```

Usada internamente por `generate_installments`, `recurrence_dates` e `generate_recurrence_occurrences`.

---

#### `bill_status(p_bill_id BIGINT) → TEXT`
**Arquivo:** `02_bill_status.sql` | **Volatilidade:** STABLE

Calcula e retorna o status derivado de uma bill. Nunca persiste — sempre computado na hora.

```sql
SELECT bill_status(42);
-- 'cancelada' | 'quitada' | 'parcial' | 'atrasada' | 'a_vencer'
-- NULL se o id não existe
```

**Lógica (em ordem de prioridade):**
1. `cancelled_at IS NOT NULL` → `cancelada`
2. `SUM(settled transactions.amount) >= bill.amount` → `quitada`
3. Algum pagamento mas incompleto → `parcial`
4. `due_date < CURRENT_DATE` sem pagamento → `atrasada`
5. Caso contrário → `a_vencer`

Usada em `list_bills` (backend) e como subtabela em `cash_flow`.

---

#### `wallet_balance(p_wallet_id BIGINT) → NUMERIC`
**Arquivo:** `03_wallet_balance.sql` | **Volatilidade:** STABLE

Calcula o saldo atual: `initial_balance + Σ(settled inflows) - Σ(settled outflows)`.

```sql
SELECT wallet_balance(1);
-- Retorna saldo atual em R$ (NULL se carteira não existe)
```

Campo `balance` no retorno de `GET /wallets` vem desta função.

---

#### `pay_bill(p_bill_id BIGINT, p_wallet_id BIGINT, p_amount NUMERIC, p_date DATE) → BIGINT`
**Arquivo:** `04_pay_bill.sql`

Quita (total ou parcialmente) uma bill criando a transação correspondente. Retorna o `id` da transação criada.

```sql
SELECT pay_bill(
  42,              -- bill_id
  1,               -- wallet_id
  500.00,          -- valor pago (pode ser parcial)
  '2024-03-15'     -- data do pagamento (DEFAULT CURRENT_DATE)
);
```

**Lógica:**
- `receivable` → gera `inflow`; `payable` → gera `outflow`
- Lança exceção se bill não existe ou está cancelada
- Pagamentos parciais são permitidos (acumula até atingir `amount`)

Chamada por `POST /bills/{id}/pay`.

---

#### `generate_installments(p_plan_id BIGINT) → INT`
**Arquivo:** `05_generate_installments.sql`

Gera N bills a partir de um `installment_plan`. Retorna o número de parcelas criadas.

```sql
SELECT generate_installments(1);
-- Cria N bills e retorna N
```

**Lógica:**
- `base_amount = trunc(total / N, 2)` — truncado em centavos
- Última parcela = `total - base * (N-1)` — absorve arredondamento
- Vencimento de cada parcela: `clamp_day(mês_i, dia_da_compra)`
- Tipo sempre `payable`; herda `category_id` e `payment_method_id` do plano

Chamada automaticamente ao criar um `installment_plan` via `POST /installment-plans`.

---

#### `recurrence_dates(p_recurrence_id BIGINT, p_from DATE, p_until DATE) → SETOF DATE`
**Arquivo:** `06_recurrence_dates.sql` | **Volatilidade:** STABLE

Função set-returning: retorna as datas de ocorrência de uma recorrência dentro de `[p_from, p_until]`. **Não grava nada** — puramente virtual.

```sql
SELECT * FROM recurrence_dates(5, '2024-01-01', '2024-12-31');
-- Retorna: 2024-01-15, 2024-02-15, 2024-03-15, ...
```

Suporte a `weekly`, `monthly`, `yearly`, `interval_count`, `end_date`, `occurrences_count`.

Usada por `generate_recurrence_occurrences` e `cash_flow`.

---

#### `generate_recurrence_occurrences(p_recurrence_id BIGINT, p_until DATE) → INT`
**Arquivo:** `07_generate_recurrence_occurrences.sql`

Materializa ocorrências de uma recorrência como bills até `p_until`, sem duplicar bills já existentes. Retorna o número de bills criadas.

```sql
SELECT generate_recurrence_occurrences(5, '2024-12-31');
```

**Lógica:**
- Usa `recurrence_dates()` para calcular datas
- Ignora datas que já têm bill com `recurrence_id = r.id AND due_date = d`
- Herda `user_id`, `type`, `description`, `amount`, `category_id`, `payment_method_id` da recorrência

Chamada por `POST /recurrences/{id}/materialize`.

---

#### `seed_default_categories(p_user_id BIGINT) → VOID`
**Arquivo:** `08_seed_default_categories.sql`

Cria 16 categorias padrão para novo usuário.

```sql
SELECT seed_default_categories(42);
```

Chamada automaticamente no `POST /auth/register`.

**Categorias criadas:**
- **Despesa (10):** Moradia, Alimentação, Transporte, Saúde, Educação, Lazer, Vestuário, Contas Fixas, Assinaturas, Outros
- **Receita (6):** Salário, Freelance, Aluguel, Dividendos, Pensão, Outros

---

#### `cash_flow(p_user_id BIGINT, p_start DATE, p_end DATE, p_granularity TEXT) → TABLE`
**Arquivo:** `09_cash_flow.sql` | **Volatilidade:** STABLE

Fluxo de caixa completo: realizado + projetado no período.

```sql
SELECT * FROM cash_flow(1, '2024-01-01', '2024-12-31', 'monthly');
```

**Colunas retornadas:**

| Coluna | Tipo | Descrição |
|---|---|---|
| `bucket` | `DATE` | Início do período (dia, semana ou mês) |
| `kind` | `TEXT` | `realized` ou `projected` |
| `inflow` | `NUMERIC` | Total de entradas no bucket |
| `outflow` | `NUMERIC` | Total de saídas no bucket |
| `net` | `NUMERIC` | `inflow - outflow` |
| `running_balance` | `NUMERIC` | Saldo acumulado desde a abertura |

**Composição:**
1. **Saldo de abertura:** `Σ initial_balance` das carteiras + todas as transactions settled antes de `p_start`
2. **Realizado:** transactions settled no período, agrupadas por bucket
3. **Projetado (bills):** bills com `status = 'a_vencer'` no futuro, agrupadas por bucket
4. **Projetado (recorrências):** recorrências com `materialize = false` — calculadas via `recurrence_dates()` sem criar bills

> Bills materializadas de recorrências aparecem no item 3 — não contadas em dobro.

---

#### `record_market_value(p_investment_id BIGINT, p_date DATE, p_price NUMERIC) → VOID`
**Arquivo:** `13_record_market_value.sql`

Upsert do preço unitário de um ativo em uma data específica.

```sql
SELECT record_market_value(10, '2024-03-15', 35.47);
```

- Registro já existe para `(investment_id, date)` → atualiza `market_value`
- Não existe → insere

Chamada por `POST /investments/{id}/quote` (manual) e `POST /investments/sync-brapi` (automático).

---

#### `invested_total(p_investment_id BIGINT) → NUMERIC`
**Arquivo:** `14_invested_total.sql` | **Volatilidade:** STABLE

Total investido: `Σ deposits - Σ withdrawals` da tabela `contributions`.

```sql
SELECT invested_total(10);
-- Ex: 5000.00
```

Campo `invested` em `GET /investments`.

---

#### `position_value(p_investment_id BIGINT) → NUMERIC`
**Arquivo:** `15_position_value.sql` | **Volatilidade:** STABLE

Valor atual da posição: `quantity × último preço unitário`. Retorna NULL se não houver cotação.

```sql
SELECT position_value(10);
-- Ex: 5847.00 (100 ações × R$ 58.47)
-- NULL se nenhuma cotação existe em value_history
```

Campo `position` em `GET /investments`.

---

#### `investment_return(p_investment_id BIGINT) → NUMERIC`
**Arquivo:** `16_investment_return.sql` | **Volatilidade:** STABLE

Rentabilidade em R$: `position_value - invested_total`. Retorna NULL se não houver cotação.

```sql
SELECT investment_return(10);
-- Ex: 847.00
-- NULL se position_value() retornar NULL
```

Campo `return_value` em `GET /investments`.

---

### Triggers

#### `tags_limit` — BEFORE INSERT ON `tags`
**Função:** `trg_tags_limit()` — `10_trg_tags_limit.sql`

Rejeita INSERT quando o usuário já possui 5 tags:
```
RAISE EXCEPTION 'Limite de 5 tags por usuário atingido'
```

---

#### `tx_type_coherence` — BEFORE INSERT OR UPDATE ON `transactions`
**Função:** `trg_tx_type_coherence()` — `11_trg_tx_type_coherence.sql`

Impede vincular categoria de tipo incompatível:
- `inflow` → só aceita categoria `income`
- `outflow` → só aceita categoria `expense`

```
RAISE EXCEPTION 'Categoria (%) incompatível com transação %'
```

---

#### `bill_type_coherence` — BEFORE INSERT OR UPDATE ON `bills`
**Função:** `trg_bill_type_coherence()` — `12_trg_bill_type_coherence.sql`

Mesma lógica para bills:
- `receivable` → só aceita categoria `income`
- `payable` → só aceita categoria `expense`

---

### Seeds

#### `db/seeds/01_payment_methods.sql`
Popula `payment_methods` com as formas de pagamento globais (executada uma vez no setup do Docker).

---

### Índices

| Índice | Tabela | Colunas | Objetivo |
|---|---|---|---|
| `idx_sessions_token` | `sessions` | `token` | Lookup de sessão em cada request |
| `idx_wallets_user` | `wallets` | `user_id` | Filtrar carteiras do usuário |
| `idx_categories_user` | `categories` | `user_id` | Filtrar categorias do usuário |
| `idx_tags_user` | `tags` | `user_id` | Filtrar tags + verificar limite |
| `idx_inst_plans_user` | `installment_plans` | `user_id` | Filtrar planos do usuário |
| `idx_recurrences_user` | `recurrences` | `user_id` | Filtrar recorrências do usuário |
| `idx_bills_user_due` | `bills` | `(user_id, due_date)` | Listar bills ordenadas por vencimento |
| `idx_bills_inst_plan` | `bills` | `installment_plan_id` | Agrupar parcelas por plano |
| `idx_bills_recurrence` | `bills` | `recurrence_id` | Verificar ocorrências já materializadas |
| `idx_transactions_user_dt` | `transactions` | `(user_id, date)` | Histórico por período |
| `idx_transactions_bill` | `transactions` | `bill_id` | Calcular `bill_status` |
| `idx_transactions_wallet` | `transactions` | `wallet_id` | Calcular `wallet_balance` |
| `idx_investments_user` | `investments` | `user_id` | Filtrar investimentos do usuário |
| `idx_value_history_inv` | `value_history` | `(investment_id, date)` | Buscar última cotação |

---

### Fluxos principais

#### 1. Cadastro de usuário

```
POST /auth/register
  → INSERT INTO users
  → SELECT seed_default_categories(user_id)
     → INSERT 16 categorias padrão (10 despesa + 6 receita)
```

#### 2. Quitar uma bill (total ou parcial)

```
POST /bills/{id}/pay { wallet_id, amount, date }
  → verificar ownership (user_id)
  → SELECT pay_bill(bill_id, wallet_id, amount, date)
     → determina tx_type: receivable→inflow, payable→outflow
     → INSERT INTO transactions (status=settled, bill_id=...)
     → RETURN transaction.id
```

#### 3. Criar parcelamento

```
POST /installment-plans { description, total_amount, total_installments, purchase_date, ... }
  → INSERT INTO installment_plans RETURNING id
  → SELECT generate_installments(plan_id)
     → para i in 1..N:
        → due = clamp_day(mês_i, dia_compra)
        → INSERT INTO bills (type=payable, amount=parcela_i, installment_plan_id=plan_id, ...)
     → RETURN N
```

#### 4. Materializar recorrência

```
POST /recurrences/{id}/materialize { until: "2024-12-31" }
  → SELECT generate_recurrence_occurrences(rid, until)
     → SELECT recurrence_dates(rid, start_date, until) → [d1, d2, ...]
     → para cada data d:
        → SE não existe bill com (recurrence_id=rid AND due_date=d):
           → INSERT INTO bills
     → RETURN count_created
```

#### 5. Fluxo de caixa

```
GET /cash-flow?start=2024-01-01&end=2024-12-31&granularity=monthly
  → SELECT * FROM cash_flow(user_id, start, end, 'monthly')
     → saldo_abertura = Σ initial_balance + Σ settled transactions antes de start
     → realizado: GROUP BY mês das transactions settled no período
     → proj_bills: bills a_vencer no futuro, agrupadas por mês
     → proj_rec: recurrence_dates() para recorrências com materialize=false
     → UNION ALL + acumular running_balance
     → RETURN TABLE (bucket, kind, inflow, outflow, net, running_balance)
```

#### 6. Sincronizar cotações via brapi

```
POST /investments/sync-brapi
  → buscar investments WHERE track_brapi=true AND user_id=uid
  → extrair símbolos únicos
  → GET brapi.dev/api/quote/{symbols}
  → para cada investment com preço disponível:
     → SELECT record_market_value(inv_id, today, price)
        → INSERT ... ON CONFLICT DO UPDATE
  → RETURN { updated: N, symbols, prices }
```

---

## Backend (FastAPI)

**Estrutura:**
```
backend/
  main.py                 # app FastAPI, inclui routers
  deps.py                 # current_user, guard()
  models/
    auth.py               # Pydantic: LoginIn, RegisterIn
    finance.py            # Pydantic: WalletIn, BillIn, TransactionIn, ...Update
    investments.py        # Pydantic: InvestmentIn, ContributionIn, QuoteIn, ...Update
  routers/
    auth.py               # /auth/*
    finance.py            # /wallets, /categories, /bills, /transactions, ...
    investments.py        # /investments/*
    chat.py               # /chat, /chats (Groq + Redis)
  services/
    auth_service.py       # login, register, sessão
    finance_service.py    # CRUD + _patch() dinâmico + chamadas às funções SQL
    investments_service.py
    db_service.py         # query_one, query_all, execute (psycopg3)
    brapi_service.py      # fetch_quotes() → brapi.dev
    memory_service.py     # chats em Redis (TTL 24h)
```

**PATCH dinâmico (`_patch()`):** backend usa allowlist por tabela (`_ALLOWED_PATCH`) — só campos explicitamente permitidos são atualizados via SQL paramétrico. Previne SQL injection por nome de coluna.

**Todos os endpoints:**

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cadastrar usuário + seed categorias |
| POST | `/auth/login` | Login → token |
| GET | `/auth/me` | Dados do usuário logado |
| POST | `/auth/logout` | Invalidar sessão |
| GET | `/wallets` | Listar carteiras + saldo calculado |
| POST | `/wallets` | Criar carteira |
| PATCH | `/wallets/{id}` | Editar carteira |
| DELETE | `/wallets/{id}` | Deletar carteira |
| GET | `/categories` | Listar categorias do usuário |
| POST | `/categories` | Criar categoria |
| PATCH | `/categories/{id}` | Editar categoria |
| DELETE | `/categories/{id}` | Deletar categoria |
| GET | `/tags` | Listar tags |
| POST | `/tags` | Criar tag (máx. 5) |
| DELETE | `/tags/{id}` | Deletar tag |
| GET | `/payment-methods` | Listar formas de pagamento |
| GET | `/bills` | Listar bills + status calculado |
| POST | `/bills` | Criar bill |
| PATCH | `/bills/{id}` | Editar bill |
| POST | `/bills/{id}/pay` | Quitar bill (chama `pay_bill()`) |
| POST | `/bills/{id}/cancel` | Cancelar bill |
| DELETE | `/bills/{id}` | Deletar bill |
| GET | `/transactions` | Listar transações |
| POST | `/transactions` | Criar transação manual |
| PATCH | `/transactions/{id}` | Editar transação |
| DELETE | `/transactions/{id}` | Deletar transação |
| GET | `/recurrences` | Listar recorrências |
| POST | `/recurrences` | Criar recorrência |
| POST | `/recurrences/{id}/materialize` | Materializar bills até data |
| POST | `/recurrences/{id}/toggle` | Ativar/desativar recorrência |
| DELETE | `/recurrences/{id}` | Deletar recorrência |
| GET | `/installment-plans` | Listar parcelamentos |
| POST | `/installment-plans` | Criar parcelamento + gerar parcelas |
| DELETE | `/installment-plans/{id}` | Deletar plano |
| GET | `/cash-flow` | Fluxo de caixa (params: start, end, granularity) |
| GET | `/investments` | Listar investimentos + métricas DB |
| POST | `/investments` | Criar investimento |
| PATCH | `/investments/{id}` | Editar investimento |
| DELETE | `/investments/{id}` | Deletar investimento |
| GET | `/investments/{id}/contributions` | Listar aportes/retiradas |
| POST | `/investments/{id}/contributions` | Adicionar aporte ou retirada |
| GET | `/investments/{id}/history` | Histórico de cotações |
| POST | `/investments/{id}/quote` | Registrar cotação manual |
| POST | `/investments/sync-brapi` | Sincronizar cotações via brapi.dev |
| GET | `/chats` | Listar chats IA (Redis) |
| POST | `/chat` | Enviar mensagem ao LLM (Groq) |

---

## Frontend (React)

**Stack:** React 18, TypeScript, Vite, Tailwind CSS, Lucide React.

**Estrutura relevante:**
```
frontend/
  App.tsx                          # Root: auth + carregamento global + tabs
  src/
    services/
      api.ts                       # Cliente HTTP base (fetch + Bearer token)
      auth.ts                      # authService: login/register/me/logout
      finance.ts                   # walletApi, categoryApi, transactionApi, billApi, investmentApi, cashFlowApi
    types/
      domain.ts                    # Tipos alinhados ao schema do banco
    components/pages/
      ReceitasTab.tsx              # Transações inflow → GET/POST/DELETE /transactions
      DespesasTab.tsx              # Transações outflow → GET/POST/DELETE /transactions
      ReceberTab.tsx               # Bills receivable → GET/POST + /pay + /cancel
      PagarTab.tsx                 # Bills payable → GET/POST + /pay + /cancel
      InvestTab.tsx                # Investimentos → GET/POST + contributions + sync-brapi
      CashFlowTab.tsx              # Fluxo de caixa → GET /cash-flow
      IATab.tsx                    # Chat IA (Groq + Redis, dados lidos da API)
```

**Padrão de carregamento (`App.tsx`):**
- `loadAll()` carrega em paralelo: wallets, categories, payment-methods, transactions, bills, investments.
- `onRefresh` é passado para cada tab — ao criar/editar/deletar qualquer item, recarrega tudo da API.
- Tabs recebem dados como props — sem `useState` local de dados financeiros.
- Zero `localStorage` para dados financeiros (token de sessão usa localStorage normalmente).

**Tipos principais (`domain.ts`) alinhados ao banco:**

| Tipo TS | Tabela DB | Campos chave |
|---|---|---|
| `Transaction` | `transactions` | `type: "inflow"\|"outflow"`, `status: "settled"\|"reversed"` |
| `Bill` | `bills` | `type: "payable"\|"receivable"`, `status` (calculado pelo DB) |
| `Investment` | `investments` | `invested`, `position`, `return_value` (funções DB) |
| `Wallet` | `wallets` | `balance` (calculado por `wallet_balance()`) |
| `Category` | `categories` | `type: "income"\|"expense"` |
| `PaymentMethod` | `payment_methods` | `id`, `name` |
