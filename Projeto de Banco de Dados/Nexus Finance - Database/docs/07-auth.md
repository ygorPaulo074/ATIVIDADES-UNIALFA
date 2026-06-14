# 07 — Autenticação (simples: usuário + senha)

> Decisão: **sem auth por email** — nada de verificação de email nem recuperação
> de senha por email (sem Mailpit/SMTP). Login/cadastro só com **usuário + senha**.

## `users`

| Coluna | Notas |
|---|---|
| `id` | PK |
| `username` | **único** — login |
| `email` | **opcional** (nullable) — guardado se informado, não usado para auth |
| `password_hash` | **bcrypt** |
| `created_at` | timestamp |

- **Cadastro** (`POST /auth/register`): cria o usuário **já ativo** e semeia as
  categorias padrão (`seed_default_categories`). Login imediato.
- **Login** (`POST /auth/login`): `username` (ou email, se houver) + senha →
  cria sessão e retorna o token.

## `sessions` (entrar direto no 2º acesso)

`id`, `user_id`, `token`, `created_at`, `expires_at`.

- Validade de **30 dias**, renovada a cada uso (desliza `expires_at`).
- Token guardado no dispositivo (localStorage); enquanto válido, entra **sem senha**.
- **Logout** (`POST /auth/logout`) remove o token.

## Segurança e isolamento

- Senhas com **bcrypt**; tokens de sessão aleatórios com expiração.
- **Isolamento**: `user_id` (FK) em todas as tabelas de dados.

> Recuperação de senha (caso volte no futuro): hoje é feita manualmente via `psql`
> (UPDATE no `password_hash`). Para reativar fluxo por email, reintroduzir tabela de
> tokens + serviço de email.
