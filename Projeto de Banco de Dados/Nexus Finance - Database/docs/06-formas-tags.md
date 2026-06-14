# 06 — Formas de Pagamento e Tags

## `payment_methods` — lista fixa (domínio)

Pré-populada (seed). O usuário **escolhe**, não cria. Formas mais comuns no Brasil:

| `id` | `name` |
|---|---|
| 1 | PIX |
| 2 | Dinheiro |
| 3 | Cartão de Débito |
| 4 | Cartão de Crédito |
| 5 | Boleto |
| 6 | Transferência (TED/DOC) |
| 7 | Outros |

- Referenciada por `payment_method_id` em `transactions`, `bills`, `recurrences`, `installment_plans`.
- Responde "quanto gastei no **PIX**?" → `SUM(amount)` agrupando por `payment_method_id`.

## `tags` — criadas pelo usuário (máx. 5), **só em transações**

| Tabela | Colunas |
|---|---|
| `tags` | `id`, `user_id`, `name` (ex.: "energia") |
| `transaction_tags` | `transaction_id`, `tag_id` — **N:N** |

- **Limite de 5 por usuário** via **trigger** `trg_tags_limit` (`BEFORE INSERT`).
- Aplicam-se **só a `transactions`** (não a bills/recurrences).
- `UNIQUE(user_id, name)` evita duplicadas.
- Responde "quanto gastei em **energia**?" → join `transaction_tags` + `SUM`.

> `payment_method` = **como** pagou (fixo); `tag` = rótulo livre do usuário (até 5).
