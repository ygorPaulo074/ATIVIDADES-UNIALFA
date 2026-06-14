# 04 — Recorrências e Fluxo de Caixa

## `recurrences` (a regra, não as ocorrências)

| Coluna | Descrição |
|---|---|
| `id`, `user_id` | PK / dono |
| `type` | `payable` \| `receivable` |
| `description`, `amount` | rótulo e valor de cada ocorrência |
| `category_id`, `payment_method_id` | classificação |
| `frequency` | `weekly` \| `monthly` \| `yearly` |
| `interval_count` | "a cada N" (monthly+2 = bimestral; weekly+2 = quinzenal) |
| `reference_day` | dia do ciclo (mês 1–31 / semana 1–7) |
| `start_date` | início da regra |
| `end_date` *ou* `occurrences_count` | fim (nullable = indefinido) |
| `materialize` | **boolean (checkbox do usuário)** — ver abaixo |
| `active` | liga/desliga sem apagar |

> Regra de borda do `reference_day`: dia inexistente no mês (ex.: 31 em fev) → último dia do mês.

## Materialização — checkbox `materialize`

- **true** → função SQL gera **`bills`** reais (cada uma editável/pagável).
  - regra finita (`end_date`/`occurrences_count`): materializa todas.
  - indefinida: materializa **janela rolante** (ex.: 12 meses), completada periodicamente.
- **false** → permanece **virtual**: aparece só na projeção do fluxo de caixa.

> Parcelamento (`05-parcelamento.md`) **sempre** materializa.

Função: `generate_recurrence_occurrences(recurrence_id, until_date)`.

## Fluxo de caixa

Função: `cash_flow(user_id, start_date, end_date, granularity)`
com `granularity` ∈ `daily` | `weekly` | `monthly` (**configurável**).

- **Realizado**: `transactions` settled + saldo acumulado a partir das `wallets`.
- **Projetado**: saldo atual + `bills` a_vencer (parcelas e recorrências materializadas)
  + ocorrências **virtuais** das recorrências não materializadas.
- **Saída**: série temporal (saldo previsto por período).
