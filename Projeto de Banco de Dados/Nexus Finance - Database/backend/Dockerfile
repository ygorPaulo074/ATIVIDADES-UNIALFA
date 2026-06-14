# Backend FastAPI + Groq — imagem Python enxuta
# Python 3.12: compatível com os pins do requirements.txt (pandas 2.2.3, pydantic 2.10.4)
FROM python:3.12-slim

WORKDIR /app

# Instala dependências primeiro para aproveitar o cache de camadas do Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação (o .env NÃO entra na imagem — ver .dockerignore;
# as variáveis são injetadas em tempo de execução via env_file no docker-compose)
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
