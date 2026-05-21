#!/usr/bin/env python3
"""
seed.py — Insere 5 registros aleatórios em cada tabela do banco 'loja'.

Dependências:
    pip install psycopg2-binary faker

Uso:
    python seed.py
    python seed.py --host localhost --port 5432 --user admin --password admin123 --dbname loja
"""

import argparse
import random
import psycopg2
from faker import Faker
from decimal import Decimal

fake = Faker("pt_BR")

# ── Conexão ──────────────────────────────────────────────────────────────────

def get_conn(host, port, user, password, dbname):
    return psycopg2.connect(
        host=host, port=port, user=user, password=password, dbname=dbname
    )

# ── Seed functions ────────────────────────────────────────────────────────────

def seed_categorias(cur):
    nomes = ["Eletrônicos", "Vestuário", "Alimentos", "Livros", "Esportes"]
    ids = []
    for nome in nomes:
        cur.execute(
            "INSERT INTO categorias (nome) VALUES (%s) ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome RETURNING id",
            (nome,),
        )
        ids.append(cur.fetchone()[0])
    print(f"  ✔ categorias: {len(ids)} registros")
    return ids


def seed_clientes(cur):
    ids = []
    for _ in range(5):
        cur.execute(
            """
            INSERT INTO clientes (nome, email, telefone, cpf)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            RETURNING id
            """,
            (
                fake.name(),
                fake.unique.email(),
                fake.phone_number()[:20],
                fake.unique.cpf(),
            ),
        )
        row = cur.fetchone()
        if row:
            ids.append(row[0])
    print(f"  ✔ clientes:   {len(ids)} registros")
    return ids


def seed_produtos(cur, categoria_ids):
    nomes_produtos = [
        ("Smartphone Galaxy X", "Eletrônico de última geração"),
        ("Camiseta Dry-Fit", "Tecido respirável, ideal para treinos"),
        ("Whey Protein 1kg", "Suplemento proteico sabor chocolate"),
        ("Python Fluente", "Livro avançado de Python"),
        ("Tênis Running Pro", "Solado com amortecimento extra"),
    ]
    ids = []
    for nome, desc in nomes_produtos:
        preco = round(random.uniform(29.90, 1999.90), 2)
        estoque = random.randint(5, 200)
        cat_id = random.choice(categoria_ids)
        cur.execute(
            """
            INSERT INTO produtos (nome, descricao, preco, estoque, categoria_id)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (nome, desc, preco, estoque, cat_id),
        )
        ids.append(cur.fetchone()[0])
    print(f"  ✔ produtos:   {len(ids)} registros")
    return ids


def seed_pedidos(cur, cliente_ids):
    status_opcoes = ["pendente", "pago", "enviado", "entregue", "cancelado"]
    ids = []
    for _ in range(5):
        cliente_id = random.choice(cliente_ids)
        status = random.choice(status_opcoes)
        cur.execute(
            "INSERT INTO pedidos (cliente_id, status) VALUES (%s, %s) RETURNING id",
            (cliente_id, status),
        )
        ids.append(cur.fetchone()[0])
    print(f"  ✔ pedidos:    {len(ids)} registros")
    return ids


def seed_itens_pedido(cur, pedido_ids, produto_ids):
    count = 0
    for pedido_id in pedido_ids:
        produtos_escolhidos = random.sample(produto_ids, k=random.randint(1, 3))
        total = Decimal("0")
        for prod_id in produtos_escolhidos:
            qty = random.randint(1, 5)
            preco = round(random.uniform(29.90, 1999.90), 2)
            cur.execute(
                """
                INSERT INTO itens_pedido (pedido_id, produto_id, quantidade, preco_unit)
                VALUES (%s, %s, %s, %s)
                """,
                (pedido_id, prod_id, qty, preco),
            )
            total += Decimal(str(preco)) * qty
            count += 1
        cur.execute("UPDATE pedidos SET total = %s WHERE id = %s", (total, pedido_id))
    print(f"  ✔ itens_pedido: {count} registros (distribuídos em 5 pedidos)")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Seed do banco loja")
    parser.add_argument("--host",     default="localhost")
    parser.add_argument("--port",     default=5432, type=int)
    parser.add_argument("--user",     default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument("--dbname",   default="loja")
    args = parser.parse_args()

    print(f"\n🔌 Conectando em {args.host}:{args.port}/{args.dbname} …")
    conn = get_conn(args.host, args.port, args.user, args.password, args.dbname)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("\n🌱 Inserindo dados …\n")
        cat_ids     = seed_categorias(cur)
        cli_ids     = seed_clientes(cur)
        prod_ids    = seed_produtos(cur, cat_ids)
        ped_ids     = seed_pedidos(cur, cli_ids)
        seed_itens_pedido(cur, ped_ids, prod_ids)
        conn.commit()
        print("\n✅ Seed concluído com sucesso!\n")
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Erro: {e}\n")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
