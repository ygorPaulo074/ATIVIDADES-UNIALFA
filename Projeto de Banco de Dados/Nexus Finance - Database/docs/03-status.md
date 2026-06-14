# 03 — Status por tipo de movimentação

Princípio: **armazenar o mínimo, derivar o resto** por função SQL.

## `bills` (competência — obrigações a pagar/receber)

- `type`: `payable` | `receivable`.
- `amount`: valor da obrigação.
- `cancelled_at` (nullable): única marcação **manual** de status.
- Pagamentos/recebimentos são **`transactions`** vinculadas (`bill_id`). Quitado = Σ delas.

### Função `bill_status(bill_id)` (derivado)

```
cancelled_at IS NOT NULL                 -> 'cancelada'
paid = SUM(transactions.amount WHERE bill_id = ...)
  paid >= amount                         -> 'quitada'
  paid > 0  (e < amount)                 -> 'parcial'
  due_date < hoje                        -> 'atrasada'
  caso contrário                         -> 'a_vencer'
```

| Status | Origem | Significado |
|---|---|---|
| `a_vencer` | derivado | em aberto, vencimento futuro |
| `atrasada` | derivado | em aberto, vencimento passado |
| `parcial` | derivado | Σ transações > 0 e < amount |
| `quitada` | derivado | Σ transações ≥ amount |
| `cancelada` | armazenado | `cancelled_at` preenchido |

> Pagamento parcial sai naturalmente: receber 120 de uma `bill` de 200 → `parcial`, restam 80.

## `transactions` (caixa — efetivadas)

| Coluna | Valores |
|---|---|
| `type` | `inflow` \| `outflow` |
| `status` | `settled` (padrão) \| `reversed` |

## Parcelas (ver `05-parcelamento.md`)

Cada parcela é uma `bill` com seu próprio `bill_status`. Status do "pai"
(`installment_plans`) é derivado: `quitada` só quando todas as parcelas estão quitadas.
