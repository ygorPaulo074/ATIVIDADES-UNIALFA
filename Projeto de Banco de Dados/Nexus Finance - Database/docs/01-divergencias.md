# 01 — Divergências: Nexus Finance × Estado atual do projeto

> Atualizado após conclusão da Fase 1 (backend) e Fase 2 (frontend → API).
> O frontend não usa mais `localStorage` para dados financeiros.

## Status da migração (junho/2026)

| Camada | Situação |
|---|---|
| **DB** | ✅ Schema + 16 funções SQL + triggers + seeds implementados |
| **Backend (FastAPI)** | ✅ Todos endpoints cobertos; PATCH/DELETE completos |
| **Frontend** | ✅ Migrado para API — zero localStorage para dados financeiros |

---

## O que mudou no frontend (vs. estado anterior em `localStorage`)

### Tipos renomeados para alinhar ao banco

| Campo antigo (localStorage) | Campo novo (API/DB) |
|---|---|
| `descricao` | `description` |
| `valor` | `amount` |
| `data` | `date` |
| `categoria` (string) | `category_id` (FK → `categories`) |
| `forma` (string) | `payment_method_id` (FK → `payment_methods`) |
| `recebido: "Sim"/"Não"` | `status: "settled" \| "pending"` |
| `pago: "Sim"/"Não"` | `status: "settled" \| "pending"` |
| `parcela: string` | removido (parcelamentos via `/installment-plans`) |
| `recorrente: "Sim"/"Não"` | removido (recorrências via `/recurrences`) |
| `ativo` | `symbol` |
| `aportado` | `invested` (calculado por `invested_total()`) |
| `valorAtual` | `position` (calculado por `position_value()`) |
| `credor` / `devedor` | `counterparty` |
| `vencimento` | `due_date` |
| `pagoEm` / `recebidoEm` | removido — quitação via `POST /bills/{id}/pay` |
| `obs` | `notes` |
| `dataCompra` | `purchase_date` |

### Estruturas unificadas

| Antes (2 tipos separados) | Agora (tipo unificado) |
|---|---|
| `Receita` + `Despesa` | `Transaction` com `type: "inflow" \| "outflow"` |
| `ReceberItem` + `PagarItem` | `Bill` com `type: "receivable" \| "payable"` |
| `Investimento` com snapshots | `Investment` com `contributions` + `value_history` |

### Recursos adicionados

- **Status de bills do banco**: `quitada`, `parcial`, `atrasada`, `a_vencer`, `cancelada` — calculados por `bill_status()` no DB, não no frontend.
- **Ação de pagar bill**: modal inline com seleção de carteira + valor parcial — chama `pay_bill()` via `POST /bills/{id}/pay`.
- **Aportes/retiradas**: modal inline em InvestTab — chama `POST /investments/{id}/contributions`.
- **Sincronização brapi**: botão em InvestTab — chama `POST /investments/sync-brapi`.
- **Fluxo de Caixa**: nova aba — chama `GET /cash-flow` com período + granularidade.
- **Wallets, categories, payment-methods**: carregados via API no App.tsx e injetados nas tabs como props.

---

## Divergências residuais (gaps ainda existentes)

| Gap | Camada | Notas |
|---|---|---|
| Tags (N:N com transações) | Frontend | Backend tem CRUD de tags; UI não expõe |
| Recorrências (criar/listar) | Frontend | Endpoints existem; UI não tem formulário |
| Parcelamentos (criar/listar) | Frontend | Endpoints existem; UI não tem formulário |
| Gestão de carteiras | Frontend | Endpoints existem; UI não tem tela de gestão |
| Gestão de categorias | Frontend | Endpoints existem; UI não tem tela de gestão |
| Export Excel | Frontend | Removido na migração (usava dados localStorage) |
| IATab — criar lançamentos via chat | Frontend | Simplificado: IA só analisa, não persiste via chat |

> As divergências acima são de **funcionalidade de UI não implementada**, não de ausência de backend ou banco.
