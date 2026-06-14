-- ============================================================
--  schema.sql — Projeto Financeiro (PostgreSQL). Sem ORM.
--  DDL: tipos, tabelas e índices. Funções/triggers: functions.sql. Seeds: seeds/.
--  Identificadores em inglês, comentários em português.
-- ============================================================

-- ===== TIPOS (ENUMs) =====
CREATE TYPE bill_type          AS ENUM ('payable', 'receivable');   -- a pagar / a receber
CREATE TYPE transaction_type   AS ENUM ('inflow', 'outflow');       -- entrada / saída
CREATE TYPE transaction_status AS ENUM ('settled', 'reversed');     -- efetivada / estornada
CREATE TYPE category_type      AS ENUM ('income', 'expense');       -- receita / despesa
CREATE TYPE frequency          AS ENUM ('weekly', 'monthly', 'yearly');
CREATE TYPE contribution_type  AS ENUM ('deposit', 'withdrawal');   -- aporte / retirada
CREATE TYPE investment_type    AS ENUM ('stock','reit','etf','bdr','crypto','treasury','fixed_income');

-- ===== AUTENTICAÇÃO =====
CREATE TABLE users (
  id            BIGSERIAL    PRIMARY KEY,
  username      VARCHAR(50)  NOT NULL UNIQUE,
  email         VARCHAR(255) UNIQUE,                     -- opcional (sem auth por email)
  password_hash TEXT         NOT NULL,                   -- bcrypt
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE sessions (
  id         BIGSERIAL   PRIMARY KEY,
  user_id    BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  token      TEXT        NOT NULL UNIQUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  expires_at TIMESTAMPTZ NOT NULL                        -- 30 dias, desliza a cada uso
);

-- ===== CADASTROS (carteiras, categorias, formas, tags) =====

-- Lista fixa/global (sem user_id) — populada em seeds/01_payment_methods.sql
CREATE TABLE payment_methods (
  id   SMALLSERIAL PRIMARY KEY,
  name VARCHAR(40) NOT NULL UNIQUE
);

-- Onde o dinheiro fica (contas bancárias / carteiras)
CREATE TABLE wallets (
  id              BIGSERIAL     PRIMARY KEY,
  user_id         BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name            VARCHAR(100)  NOT NULL,
  initial_balance NUMERIC(14,2) NOT NULL DEFAULT 0,
  created_at      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Categorias por usuário; semeadas no cadastro (seed_default_categories), editáveis
CREATE TABLE categories (
  id      BIGSERIAL     PRIMARY KEY,
  user_id BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name    VARCHAR(60)   NOT NULL,
  type    category_type NOT NULL,
  UNIQUE (user_id, name, type)
);

-- Máx. 5 por usuário (trigger em functions.sql)
CREATE TABLE tags (
  id      BIGSERIAL   PRIMARY KEY,
  user_id BIGINT      NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name    VARCHAR(30) NOT NULL,
  UNIQUE (user_id, name)
);

-- ===== CONTAS / OBRIGAÇÕES (parcelamentos, recorrências, contas) =====

-- Compra parcelada (pai)
CREATE TABLE installment_plans (
  id                 BIGSERIAL     PRIMARY KEY,
  user_id            BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  description        VARCHAR(120)  NOT NULL,
  total_amount       NUMERIC(14,2) NOT NULL CHECK (total_amount > 0),
  total_installments INT           NOT NULL CHECK (total_installments > 0),
  category_id        BIGINT        REFERENCES categories(id)      ON DELETE SET NULL,
  payment_method_id  SMALLINT      REFERENCES payment_methods(id) ON DELETE RESTRICT,
  purchase_date      DATE          NOT NULL,
  created_at         TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- Regra de recorrência (não as ocorrências)
CREATE TABLE recurrences (
  id                BIGSERIAL     PRIMARY KEY,
  user_id           BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type              bill_type     NOT NULL,
  description       VARCHAR(120)  NOT NULL,
  amount            NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  category_id       BIGINT        REFERENCES categories(id)      ON DELETE SET NULL,
  payment_method_id SMALLINT      REFERENCES payment_methods(id) ON DELETE RESTRICT,
  frequency         frequency     NOT NULL,
  interval_count    INT           NOT NULL DEFAULT 1 CHECK (interval_count > 0),  -- "a cada N"
  reference_day     INT           NOT NULL CHECK (reference_day BETWEEN 1 AND 31),
  start_date        DATE          NOT NULL,
  end_date          DATE,
  occurrences_count INT           CHECK (occurrences_count IS NULL OR occurrences_count > 0),
  materialize       BOOLEAN       NOT NULL DEFAULT true,
  active            BOOLEAN       NOT NULL DEFAULT true,
  CONSTRAINT recurrence_end_exclusive
    CHECK (NOT (end_date IS NOT NULL AND occurrences_count IS NOT NULL))  -- end_date XOR count
);

-- Obrigações a pagar/receber (competência). Status derivado por bill_status().
CREATE TABLE bills (
  id                  BIGSERIAL     PRIMARY KEY,
  user_id             BIGINT        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type                bill_type     NOT NULL,
  description         VARCHAR(120)  NOT NULL,
  amount              NUMERIC(14,2) NOT NULL CHECK (amount > 0),
  due_date            DATE          NOT NULL,
  counterparty        VARCHAR(120),                          -- devedor / credor
  category_id         BIGINT        REFERENCES categories(id)        ON DELETE SET NULL,
  payment_method_id   SMALLINT      REFERENCES payment_methods(id)   ON DELETE RESTRICT,
  recurrence_id       BIGINT        REFERENCES recurrences(id)       ON DELETE SET NULL,
  installment_plan_id BIGINT        REFERENCES installment_plans(id) ON DELETE CASCADE,
  installment_number  INT,
  cancelled_at        TIMESTAMPTZ,                           -- única marcação manual de status
  created_at          TIMESTAMPTZ   NOT NULL DEFAULT now(),
  CONSTRAINT bill_installment_coherent
    CHECK (installment_number IS NULL OR installment_plan_id IS NOT NULL)
);

-- ===== TRANSAÇÕES (caixa) =====
CREATE TABLE transactions (
  id                BIGSERIAL          PRIMARY KEY,
  user_id           BIGINT             NOT NULL REFERENCES users(id)   ON DELETE CASCADE,
  wallet_id         BIGINT             NOT NULL REFERENCES wallets(id) ON DELETE CASCADE,
  type              transaction_type   NOT NULL,
  description       VARCHAR(120)       NOT NULL,
  amount            NUMERIC(14,2)      NOT NULL CHECK (amount > 0),
  date              DATE               NOT NULL,
  category_id       BIGINT             REFERENCES categories(id)      ON DELETE SET NULL,
  payment_method_id SMALLINT           REFERENCES payment_methods(id) ON DELETE RESTRICT,
  bill_id           BIGINT             REFERENCES bills(id)           ON DELETE SET NULL,
  status            transaction_status NOT NULL DEFAULT 'settled',
  notes             TEXT,
  created_at        TIMESTAMPTZ        NOT NULL DEFAULT now()
);

-- N:N transações <-> tags
CREATE TABLE transaction_tags (
  transaction_id BIGINT NOT NULL REFERENCES transactions(id) ON DELETE CASCADE,
  tag_id         BIGINT NOT NULL REFERENCES tags(id)         ON DELETE CASCADE,
  PRIMARY KEY (transaction_id, tag_id)
);

-- ===== INVESTIMENTOS =====
CREATE TABLE investments (
  id            BIGSERIAL       PRIMARY KEY,
  user_id       BIGINT          NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  symbol        VARCHAR(60)     NOT NULL,            -- ticker do brapi (PETR4, BTC...)
  type          investment_type NOT NULL,
  quantity      NUMERIC(18,8)   NOT NULL DEFAULT 0 CHECK (quantity >= 0),  -- frações/cripto
  currency      CHAR(3)         NOT NULL DEFAULT 'BRL',
  track_brapi   BOOLEAN         NOT NULL DEFAULT false,
  purchase_date DATE            NOT NULL,
  maturity_date DATE,                                -- renda fixa
  notes         TEXT,
  created_at    TIMESTAMPTZ     NOT NULL DEFAULT now()
);

CREATE TABLE contributions (
  id            BIGSERIAL         PRIMARY KEY,
  investment_id BIGINT            NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
  type          contribution_type NOT NULL,
  amount        NUMERIC(14,2)     NOT NULL CHECK (amount > 0),
  date          DATE              NOT NULL,
  notes         TEXT
);

-- market_value = preço UNITÁRIO do dia (brapi: close / regularMarketPrice)
CREATE TABLE value_history (
  id            BIGSERIAL     PRIMARY KEY,
  investment_id BIGINT        NOT NULL REFERENCES investments(id) ON DELETE CASCADE,
  date          DATE          NOT NULL,
  market_value  NUMERIC(18,8) NOT NULL CHECK (market_value > 0),
  UNIQUE (investment_id, date)
);

-- ===== ÍNDICES =====
CREATE INDEX idx_sessions_token       ON sessions(token);
CREATE INDEX idx_wallets_user         ON wallets(user_id);
CREATE INDEX idx_categories_user      ON categories(user_id);
CREATE INDEX idx_tags_user            ON tags(user_id);
CREATE INDEX idx_inst_plans_user      ON installment_plans(user_id);
CREATE INDEX idx_recurrences_user     ON recurrences(user_id);
CREATE INDEX idx_bills_user_due       ON bills(user_id, due_date);
CREATE INDEX idx_bills_inst_plan      ON bills(installment_plan_id);
CREATE INDEX idx_bills_recurrence     ON bills(recurrence_id);
CREATE INDEX idx_transactions_user_dt ON transactions(user_id, date);
CREATE INDEX idx_transactions_bill    ON transactions(bill_id);
CREATE INDEX idx_transactions_wallet  ON transactions(wallet_id);
CREATE INDEX idx_investments_user     ON investments(user_id);
CREATE INDEX idx_value_history_inv    ON value_history(investment_id, date);
