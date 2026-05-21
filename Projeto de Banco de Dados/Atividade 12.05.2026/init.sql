-- ============================================================
--  SCHEMA: loja
-- ============================================================

-- Clientes
CREATE TABLE clientes (
    id          SERIAL PRIMARY KEY,
    nome        VARCHAR(120)        NOT NULL,
    email       VARCHAR(180)        UNIQUE NOT NULL,
    telefone    VARCHAR(20),
    cpf         VARCHAR(14)         UNIQUE NOT NULL,
    criado_em   TIMESTAMP           DEFAULT NOW()
);

-- Categorias de produtos
CREATE TABLE categorias (
    id      SERIAL PRIMARY KEY,
    nome    VARCHAR(80) UNIQUE NOT NULL
);

-- Produtos
CREATE TABLE produtos (
    id           SERIAL PRIMARY KEY,
    nome         VARCHAR(120)        NOT NULL,
    descricao    TEXT,
    preco        NUMERIC(10, 2)      NOT NULL CHECK (preco >= 0),
    estoque      INTEGER             NOT NULL DEFAULT 0 CHECK (estoque >= 0),
    categoria_id INTEGER             REFERENCES categorias(id) ON DELETE SET NULL,
    criado_em    TIMESTAMP           DEFAULT NOW()
);

-- Pedidos
CREATE TABLE pedidos (
    id           SERIAL PRIMARY KEY,
    cliente_id   INTEGER         NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    status       VARCHAR(30)     NOT NULL DEFAULT 'pendente'
                                 CHECK (status IN ('pendente', 'pago', 'enviado', 'entregue', 'cancelado')),
    total        NUMERIC(10, 2)  NOT NULL DEFAULT 0,
    criado_em    TIMESTAMP       DEFAULT NOW()
);

-- Itens dos pedidos  (tabela correlacionada entre pedidos e produtos)
CREATE TABLE itens_pedido (
    id          SERIAL PRIMARY KEY,
    pedido_id   INTEGER         NOT NULL REFERENCES pedidos(id)  ON DELETE CASCADE,
    produto_id  INTEGER         NOT NULL REFERENCES produtos(id) ON DELETE RESTRICT,
    quantidade  INTEGER         NOT NULL CHECK (quantidade > 0),
    preco_unit  NUMERIC(10, 2)  NOT NULL CHECK (preco_unit >= 0)
);
