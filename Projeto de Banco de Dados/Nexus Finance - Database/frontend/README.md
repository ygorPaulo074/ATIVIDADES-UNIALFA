# Frontend — Controle Financeiro (React + Vite + TypeScript)

Interface de controle financeiro pessoal (contas a pagar / a receber e
categorias), com uma aba de análise por IA que consome o backend.

## Rodar com Docker

```bash
docker compose up --build
```
App em http://localhost:5173. O proxy do Vite encaminha `/api/*` para o backend
(`http://backend:8000` dentro da rede Docker — ver `vite.config.ts`).

## Rodar sem Docker (dev local)

```bash
npm install
npm run dev
```
Nesse modo o proxy aponta para `http://localhost:8000` (rode o backend à parte).
Para customizar o destino: `VITE_PROXY_TARGET=http://host:porta npm run dev`.

## Build de produção

```bash
npm run build && npm run preview
```
