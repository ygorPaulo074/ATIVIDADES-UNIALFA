# 02 — DER (Modelo de Dados) — Documento Mestre

> Fonte única de verdade do schema. Consolida os docs `00`, `03`–`07`.
> PostgreSQL · **SQL explícito, sem ORM** · lógica em **funções PL/pgSQL**.
> **Identificadores em inglês, comentários/docs em português.**
> Convenções: PK `BIGSERIAL`; dinheiro `NUMERIC(14,2)` com `CHECK (> 0)`; datas `DATE`;
> carimbos `TIMESTAMPTZ`. **Moeda única: BRL** (sinal vem do `type`, não do valor).

## Tipos ENUM

```
bill_type          : 'payable' | 'receivable'      -- a pagar / a receber
transaction_type   : 'inflow' | 'outflow'          -- entrada / saída
transaction_status : 'settled' | 'reversed'        -- efetivada / estornada
category_type      : 'income' | 'expense'          -- receita / despesa
frequency          : 'weekly' | 'monthly' | 'yearly'
contribution_type  : 'deposit' | 'withdrawal'      -- aporte / retirada
investment_type    : 'stock' | 'reit' | 'etf' | 'bdr' | 'crypto' | 'treasury' | 'fixed_income'
```

> Status de **`bills`** NÃO é coluna — é **derivado** por função (ver `03-status.md`).

---

## Autenticação

> Auth **simples**: usuário + senha, sem verificação/recuperação por email (ver `07-auth.md`).

### `users`
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| username | VARCHAR(50) | UNIQUE, NOT NULL |
| email | VARCHAR(255) | UNIQUE, **nullable** (opcional) |
| password_hash | TEXT | NOT NULL (bcrypt) |
| created_at | TIMESTAMPTZ | NOT NULL DEFAULT now() |

### `sessions`
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| token | TEXT | UNIQUE, NOT NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |
| expires_at | TIMESTAMPTZ | NOT NULL (30 dias, desliza) |

---

## Domínio financeiro

### `wallets` (contas bancárias / onde o dinheiro fica)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| name | VARCHAR(100) | NOT NULL |
| initial_balance | NUMERIC(14,2) | NOT NULL DEFAULT 0 |
| created_at | TIMESTAMPTZ | DEFAULT now() |

> Saldo atual = `initial_balance` + Σ transações (função `wallet_balance`).

### `categories`
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| name | VARCHAR(60) | NOT NULL |
| type | category_type | NOT NULL |
| | | UNIQUE(user_id, name, type) |

> Por usuário (Opção A); semeadas no cadastro, editáveis pelo dono.

### `payment_methods` (fixa / global — sem user_id)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | SMALLSERIAL | PK |
| name | VARCHAR(40) | UNIQUE, NOT NULL |

Seed: PIX, Dinheiro, Cartão de Débito, Cartão de Crédito, Boleto, Transferência (TED/DOC), Outros.

### `tags` (máx. 5 por usuário)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| name | VARCHAR(30) | NOT NULL · UNIQUE(user_id, name) |

> Trigger `trg_tags_limit` bloqueia a 6ª tag.

### `installment_plans` (compra parcelada — o "pai")
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| description | VARCHAR(120) | NOT NULL |
| total_amount | NUMERIC(14,2) | NOT NULL CHECK > 0 |
| total_installments | INT | NOT NULL CHECK > 0 |
| category_id | BIGINT | FK→categories |
| payment_method_id | SMALLINT | FK→payment_methods |
| purchase_date | DATE | NOT NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `recurrences` (a regra)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| type | bill_type | NOT NULL |
| description | VARCHAR(120) | NOT NULL |
| amount | NUMERIC(14,2) | NOT NULL CHECK > 0 |
| category_id | BIGINT | FK→categories |
| payment_method_id | SMALLINT | FK→payment_methods |
| frequency | frequency | NOT NULL |
| interval_count | INT | NOT NULL DEFAULT 1 ("a cada N") |
| reference_day | INT | NOT NULL (dia do mês 1–31 / semana 1–7) |
| start_date | DATE | NOT NULL |
| end_date | DATE | NULL |
| occurrences_count | INT | NULL |
| materialize | BOOLEAN | NOT NULL DEFAULT true |
| active | BOOLEAN | NOT NULL DEFAULT true |

> `CHECK`: `end_date` e `occurrences_count` são **mutuamente exclusivos**.

### `bills` (obrigações a pagar/receber — competência)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| type | bill_type | NOT NULL |
| description | VARCHAR(120) | NOT NULL |
| amount | NUMERIC(14,2) | NOT NULL CHECK > 0 |
| due_date | DATE | NOT NULL |
| counterparty | VARCHAR(120) | NULL (devedor/credor) |
| category_id | BIGINT | FK→categories |
| payment_method_id | SMALLINT | FK→payment_methods |
| recurrence_id | BIGINT | FK→recurrences, NULL |
| installment_plan_id | BIGINT | FK→installment_plans, NULL |
| installment_number | INT | NULL |
| cancelled_at | TIMESTAMPTZ | NULL (única marcação manual) |
| created_at | TIMESTAMPTZ | DEFAULT now() |

> Status (`a_vencer`/`atrasada`/`parcial`/`quitada`/`cancelada`) = função `bill_status`.

### `transactions` (movimentações efetivadas — caixa)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| wallet_id | BIGINT | FK→wallets, NOT NULL |
| type | transaction_type | NOT NULL |
| description | VARCHAR(120) | NOT NULL |
| amount | NUMERIC(14,2) | NOT NULL CHECK > 0 |
| date | DATE | NOT NULL |
| category_id | BIGINT | FK→categories, NULL |
| payment_method_id | SMALLINT | FK→payment_methods |
| bill_id | BIGINT | FK→bills, NULL (preenchido ao quitar uma conta) |
| status | transaction_status | NOT NULL DEFAULT 'settled' |
| notes | TEXT | NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `transaction_tags` (N:N — tags só em transações)
| Coluna | Tipo | Constraints |
|---|---|---|
| transaction_id | BIGINT | FK→transactions |
| tag_id | BIGINT | FK→tags |
| | | PK(transaction_id, tag_id) |

---

## Investimentos

### `investments`
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| user_id | BIGINT | FK→users, NOT NULL |
| symbol | VARCHAR(60) | NOT NULL (ticker brapi: PETR4, BTC) |
| type | investment_type | NOT NULL |
| quantity | NUMERIC(18,8) | NOT NULL DEFAULT 0 (frações/cripto) |
| currency | CHAR(3) | NOT NULL DEFAULT 'BRL' (só exibição) |
| track_brapi | BOOLEAN | NOT NULL DEFAULT false |
| purchase_date | DATE | NOT NULL |
| maturity_date | DATE | NULL (renda fixa) |
| notes | TEXT | NULL |
| created_at | TIMESTAMPTZ | DEFAULT now() |

### `contributions` (histórico de aportes/retiradas)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| investment_id | BIGINT | FK→investments, NOT NULL |
| type | contribution_type | NOT NULL |
| amount | NUMERIC(14,2) | NOT NULL CHECK > 0 |
| date | DATE | NOT NULL |
| notes | TEXT | NULL |

### `value_history` (série temporal de valor de mercado)
| Coluna | Tipo | Constraints |
|---|---|---|
| id | BIGSERIAL | PK |
| investment_id | BIGINT | FK→investments, NOT NULL |
| date | DATE | NOT NULL |
| market_value | NUMERIC(18,8) | NOT NULL CHECK > 0 — **preço unitário** (brapi close) |
| | | UNIQUE(investment_id, date) |

> Valor da posição = `quantity` × último preço; investido = Σ `contributions`; ambos **derivados** por função.

### Integração brapi.dev (cotações — task #15)
- `investments.track_brapi = true` → job consulta `GET /quote/{symbol}` (`regularMarketPrice`)
  e insere/atualiza `value_history` (fechamento diário). Aportes seguem **manuais**.
- Requer `BRAPI_TOKEN` no `.env` (grátis cobre só PETR4, MGLU3, VALE3, ITUB4).

---

## Relacionamentos

```
users 1──N wallets, categories, tags, bills, transactions,
           recurrences, installment_plans, investments, sessions, *_tokens

wallets           1──N transactions
categories        1──N transactions, bills, recurrences, installment_plans
payment_methods   1──N transactions, bills, recurrences, installment_plans
recurrences       1──N bills              (ocorrências materializadas)
installment_plans 1──N bills              (parcelas-filhas)
bills             1──N transactions       (pagamentos; parcial = N)
transactions      N──N tags               (via transaction_tags)
investments       1──N contributions, value_history
```

---

## Integridade (ON DELETE) e validações

**ON DELETE:**
- `CASCADE`: dados do usuário (ao excluir `users`), `sessions`,
  `transaction_tags`, `contributions`, `value_history`, parcelas (`installment_plan_id`),
  transações da carteira (`wallet_id`).
- `SET NULL`: `category_id`, `bill_id` (transactions), `recurrence_id` (bills).
- `RESTRICT`: `payment_methods` em uso.

**Validações / triggers:**
- `trg_tags_limit` — bloqueia a 6ª tag por usuário.
- `trg_type_coherence` — coerência `inflow↔income` / `outflow↔expense` (transactions) e
  `receivable↔income` / `payable↔expense` (bills) quando há categoria.
- `CHECK (... > 0)` em valores monetários.
- `recurrences`: `CHECK` de `end_date` XOR `occurrences_count`.
- `wallet_balance` e fluxo de caixa contam só `transactions.status = 'settled'`.

## Funções SQL (PL/pgSQL) — o backend só as chama

| Função | Papel |
|---|---|
| `bill_status(bill_id)` | Deriva status (a_vencer/atrasada/parcial/quitada/cancelada) |
| `wallet_balance(wallet_id)` | initial_balance + Σ transações settled |
| `pay_bill(bill_id, wallet_id, amount, date)` | Cria a transação que quita (total/parcial) a conta |
| `generate_installments(installment_plan_id)` | Cria as N parcelas (última absorve arredondamento) |
| `generate_recurrence_occurrences(recurrence_id, until_date)` | Materializa ocorrências em `bills` |
| `cash_flow(user_id, start_date, end_date, granularity)` | Série temporal: realizado + projetado |
| `record_market_value(investment_id, date, price)` | Upsert do preço unitário (job brapi) |
| `invested_total(id)` / `position_value(id)` / `investment_return(id)` | Métricas de investimento |

## Índices

- FKs (`user_id`, `wallet_id`, `category_id`, `bill_id`, `investment_id`…).
- `bills(user_id, due_date)`, `bills(installment_plan_id)`, `bills(recurrence_id)`.
- `transactions(user_id, date)`, `transactions(bill_id)`, `transactions(wallet_id)`.
- `value_history(investment_id, date)`, `sessions(token)`.
