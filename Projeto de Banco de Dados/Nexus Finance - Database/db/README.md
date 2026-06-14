# Banco de Dados — PostgreSQL (SQL explícito, sem ORM)

Todo o schema e a lógica são escritos **à mão** em SQL, separados por camada.
Identificadores em inglês, comentários em português.

```
db/
├── schema.sql      DDL: tipos, tabelas e índices
├── functions/      uma função/trigger por arquivo (numerados p/ ordem de init)
│   ├── 01_clamp_day.sql            06_recurrence_dates.sql
│   ├── 02_bill_status.sql          07_generate_recurrence_occurrences.sql
│   ├── 03_wallet_balance.sql       08_seed_default_categories.sql
│   ├── 04_pay_bill.sql             09_cash_flow.sql
│   ├── 05_generate_installments.sql 10_trg_tags_limit.sql
│   ├── 11_trg_tx_type_coherence.sql
│   └── 12_trg_bill_type_coherence.sql
├── seeds/
│   └── 01_payment_methods.sql   dados iniciais (lista fixa)
├── migrations/     alterações versionadas posteriores
└── docker-compose.yml
```

## Rodar só o banco

```bash
docker compose up --build
```
Postgres em `localhost:5432`. Credenciais padrão: `postgres/postgres`
(banco `postgres`) — sobrescreva via `.env` na raiz do projeto.

## Como os scripts são aplicados

O Postgres executa os arquivos montados em `/docker-entrypoint-initdb.d/`
**apenas na primeira criação do volume**, em ordem: `schema.sql` → `functions.sql`
→ seeds (prefixo numérico no container controla a sequência).

Reaplicar do zero (apaga os dados):

```bash
docker compose down -v && docker compose up --build
```

Aplicar um script manualmente em um banco já rodando:

```bash
docker exec -i pf-db psql -U postgres -d postgres < seeds/01_payment_methods.sql
```
