"""
AI-ChatBot application entry point.
Rate limiting and CORS are handled by the Yopa Proxy (integrated deploy)
or by Caddy (self-hosted deploy via docker-compose.selfhosted.yml).
"""
from fastapi import FastAPI

from src.interfaces.http.routes.agent import router as agent_router
from src.interfaces.http.routes.chat import router as chat_router
from src.interfaces.http.routes.data import router as data_router
from src.interfaces.http.routes.admin import router as admin_router
from src.interfaces.http.routes.health import router as health_router
from src.interfaces.http.routes.dev import router as dev_router

app = FastAPI()

app.include_router(health_router)
app.include_router(dev_router)
app.include_router(agent_router)
app.include_router(chat_router)
app.include_router(data_router)
app.include_router(admin_router)
