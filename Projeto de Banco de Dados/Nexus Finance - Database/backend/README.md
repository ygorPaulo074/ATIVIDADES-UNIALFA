# Backend — FastAPI

Duas frentes:
- **IA** — chat com Groq (Llama 3.3) + busca Tavily + análise de extrato CSV.
  Estado em **Redis** (TTL 24h).
- **Financeiro** — auth (psycopg → funções SQL do Postgres, sem ORM).

## Configuração

```bash
cp .env.example .env   # GROQ_API_KEY, TAVILY_API_KEY, DATABASE_URL, REDIS_URL, BRAPI_TOKEN
```
Na stack (Docker), `DATABASE_URL`/`REDIS_URL` já vêm do `docker-compose.yml`.
Auth simples: **usuário + senha** (sem verificação/recuperação por email).

## Rodar com Docker

```bash
docker compose up --build
```
- API: http://localhost:8000 · Docs: http://localhost:8000/docs · Health: /health

## Rodar sem Docker (dev local)

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Endpoints

| Método | Rota | Função |
|---|---|---|
| GET | `/health` | Status do serviço |
| POST | `/chat` | Mensagem ao assistente (com tool use de busca) |
| GET/POST | `/chats` | Listar / criar chats |
| DELETE | `/chats/{id}` | Excluir chat |
| POST | `/upload-extrato` | Enviar CSV de extrato para análise |
| POST | `/auth/register` | Cadastro (usuário + senha; semeia categorias) |
| POST | `/auth/login` | Login (usuário + senha) → token de sessão |
| GET | `/auth/me` | Usuário da sessão (header `Authorization: Bearer`) |
| POST | `/auth/logout` | Encerra a sessão |

### Financeiro (exige sessão: header `Authorization: Bearer <token>`)

| Método | Rota | Função |
|---|---|---|
| GET/POST/DELETE | `/wallets` `/wallets/{id}` | Carteiras (saldo via `wallet_balance`) |
| GET/POST/DELETE | `/categories` `/tags` `/payment-methods` | Cadastros (tags: máx. 5) |
| GET/POST | `/bills` | Contas (status derivado por `bill_status`) |
| POST | `/bills/{id}/pay` · `/bills/{id}/cancel` | Quitar (`pay_bill`) / cancelar |
| GET/POST/DELETE | `/transactions` | Movimentações |
| GET/POST | `/recurrences` · `/recurrences/{id}/materialize` | Recorrências |
| GET/POST | `/installment-plans` | Parcelamentos (gera parcelas) |
| GET | `/cash-flow?start&end&granularity` | Fluxo de caixa (realizado + projetado) |
| GET/POST/DELETE | `/investments` `/investments/{id}` | Investimentos (com `invested`/`position`/`return`) |
| POST | `/investments/{id}/contributions` | Aporte / retirada |
| GET | `/investments/{id}/history` | Série de preços (value_history) |
| POST | `/investments/{id}/quote` | Lança preço manual (`record_market_value`) |
| POST | `/investments/sync-brapi` | Sincroniza cotações via brapi (`track_brapi`) |
