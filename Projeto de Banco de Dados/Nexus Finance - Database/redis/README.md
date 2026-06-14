# Redis — camada de IA efêmera

Guarda o estado da IA (chats, mensagens, extratos importados) com **TTL de 24h**.
Cada gravação renova a expiração, então a janela conta a partir da última atividade.
É transitório por natureza — **sem volume**; o banco financeiro (Postgres) não usa o Redis.

## Rodar só o Redis

```bash
docker compose up
```
Redis em `localhost:6379`. O backend o acessa por `REDIS_URL` (na stack: `redis://redis:6379/0`).

## Inspecionar

```bash
docker exec -it pf-redis redis-cli
> KEYS chat:*          # chats vivos
> TTL chat:<id>        # segundos até expirar (~86400)
```
