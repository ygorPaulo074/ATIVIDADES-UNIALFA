import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from routers.chat import router as chat_router
from routers.auth import router as auth_router
from routers.finance import router as finance_router
from routers.investments import router as investments_router

# Carrega as variáveis do arquivo .env para o ambiente Python
# Isso garante que GROQ_API_KEY, CORS_ORIGIN etc. fiquem disponíveis via os.getenv()
load_dotenv()

# Instancia o app FastAPI com metadados para a documentação automática em /docs
app = FastAPI(
    title="Chatbot Groq",
    description="Backend do chatbot com Groq (Llama 3) e busca na web via Tavily",
    version="1.0.0",
)

# Lê a origem permitida do .env — padrão é o endereço do Vite em desenvolvimento
# Sem isso, o browser bloquearia qualquer requisição do frontend para o backend
cors_origin = os.getenv("CORS_ORIGIN", "http://localhost:5173")

# Configura o middleware de CORS
# allow_credentials=True permite envio de cookies/headers de autenticação (preparação futura)
# allow_methods e allow_headers com ["*"] permitem qualquer método HTTP e header
app.add_middleware(
    CORSMiddleware,
    allow_origins=[cors_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Registra o router de chat no app principal
# Todos os endpoints definidos em routers/chat.py ficam disponíveis automaticamente
app.include_router(chat_router)
app.include_router(auth_router)
app.include_router(finance_router)
app.include_router(investments_router)


# Endpoint de verificação de saúde — usado para confirmar que o servidor está no ar
# Retorna o nome do modelo fixo para que o frontend saiba qual IA está em uso
@app.get("/health")
def health_check():
    return {"status": "ok", "model": "llama-3.3-70b-versatile"}
