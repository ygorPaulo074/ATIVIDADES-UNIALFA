## Explicação da Atividade

Desenvoler 3 scripts de SELECT de acordo com o que foi orientado em sala de aula

Os scripts desenvolvidos interagem com o banco gerado com o compose e alimentado com o seeds.py

# 🗄️ loja — banco de dados de exemplo

## Estrutura das tabelas

```
clientes
    └── pedidos
            └── itens_pedido ──► produtos
                                     └── categorias
```

| Tabela         | Descrição                                      |
|----------------|------------------------------------------------|
| `clientes`     | Dados cadastrais dos clientes                  |
| `categorias`   | Categorias de produtos                         |
| `produtos`     | Catálogo de produtos com preço e estoque       |
| `pedidos`      | Pedidos realizados por clientes                |
| `itens_pedido` | Itens (produto + quantidade) dentro de pedidos |

---

```
--host      (padrão: localhost)
--port      (padrão: 5432)
--user      (padrão: admin)
--password  (padrão: admin123)
--dbname    (padrão: loja)
```