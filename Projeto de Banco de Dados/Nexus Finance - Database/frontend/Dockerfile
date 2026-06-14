# Frontend React + Vite (modo desenvolvimento)
# Node 20 LTS — compatível com Vite 5
FROM node:20-alpine

WORKDIR /app

# Instala dependências primeiro (cache de camadas)
COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173

# --host 0.0.0.0 torna o dev server acessível fora do container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
