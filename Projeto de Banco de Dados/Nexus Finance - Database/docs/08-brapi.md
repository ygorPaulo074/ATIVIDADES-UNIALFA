# 08 — Integração brapi.dev (cotações de investimentos)

Fonte de cotações em tempo real e histórico para `investments` / `value_history`.
Feature do fim do projeto (depende do backend, task #17).

## API

- Base: `https://brapi.dev/api`
- **Cotação atual:** `GET /quote/{tickers}` (vírgula p/ vários: `PETR4,VALE3`)
  → `regularMarketPrice`, `regularMarketChange(Percent)`, `currency`, `regularMarketTime`.
- **Histórico:** `GET /quote/{ticker}?range=1mo&interval=1d`
  → array `historicalDataPrice[]` com `{ date, close, open, high, low, volume }`.
  `range`: 1d…5y,max · `interval`: 1m…1mo · ou `startDate`/`endDate` (YYYY-MM-DD).
- **Cripto:** `GET /v2/crypto?coin=BTC` · **Moedas:** `GET /v2/currency`.
- **Auth:** `Authorization: Bearer <BRAPI_TOKEN>` (token em brapi.dev/dashboard).
  Grátis sem token = só PETR4, MGLU3, VALE3, ITUB4.

## Mapeamento para o banco

| brapi | banco |
|---|---|
| `symbol` | `investments.symbol` |
| `regularMarketPrice` / `historicalDataPrice[].close` | preço unitário do dia |
| `historicalDataPrice[].date` | `value_history.date` |

## Fluxo de sincronização (backend — task #17)

1. Seleciona `investments WHERE track_brapi = true`.
2. Agrupa `symbol`s e chama `GET /quote/{symbols}?range=...&interval=1d`.
3. Para cada dia retornado, faz **upsert** em `value_history`
   (função SQL `record_market_value`, respeitando `UNIQUE(investment_id, date)`).
4. Roda como job agendado (ex.: 1×/dia após fechamento) e/ou sob demanda.

Config: `BRAPI_TOKEN` no `.env` do backend.

## ⚠️ Decisão pendente — preço unitário × quantidade

`value_history.market_value` hoje guarda um **valor**, mas o brapi devolve **preço
por unidade**. Para o valor da posição precisamos da **quantidade**, que o modelo
**não tem** (nem em `investments`, nem em `contributions`).

**Recomendação:** adicionar `investments.quantity NUMERIC(18,8)` (suporta frações/cripto)
e tratar `value_history.market_value` como **preço unitário**. Aí:

- valor da posição (leitura) = `quantity × último preço`
- `invested_total` = Σ deposits − Σ withdrawals (de `contributions`, em R$)
- `investment_return` = valor da posição − `invested_total`

Funções SQL a criar após a decisão: `record_market_value(investment_id, date, price)`,
`position_value(investment_id)`, `invested_total(investment_id)`, `investment_return(investment_id)`.
