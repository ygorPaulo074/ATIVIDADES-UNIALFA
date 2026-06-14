# 05 — Parcelamento

Modelo **pai + filhas**: a compra vive em `installment_plans`; cada parcela é uma `bill`.

## `installment_plans` (o "pai")

| Coluna | Exemplo |
|---|---|
| `id`, `user_id` | PK / dono |
| `description` | "Notebook" |
| `total_amount` | 1000.00 |
| `total_installments` | 5 |
| `category_id`, `payment_method_id` | herdados pelas parcelas |
| `purchase_date` | 2026-06-08 |

## `bills` (cada parcela-filha)

Colunas relevantes em `bills`:

| Coluna | Exemplo |
|---|---|
| `installment_plan_id` (FK, nullable) | aponta para o pai |
| `installment_number` | 1, 2, 3, 4, 5 |
| `amount` | 200.00 |
| `due_date` | mês a mês |

- `bill` sem `installment_plan_id` = avulsa (não parcelada).
- Status de cada parcela: `bill_status` (ver `03-status.md`).
- Status do pai é **derivado**: `quitada` só quando todas as filhas estão quitadas.

## Geração: `generate_installments(installment_plan_id)`

- Cria as `total_installments` filhas (parcelamento **sempre** materializa).
- **Arredondamento**: última parcela absorve a diferença.
  Ex.: 1000 ÷ 3 → 333.33 + 333.33 + **333.34**.
- Vencimentos mês a mês (regra de borda do dia igual à de recorrências).
