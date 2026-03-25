# Set up path FIRST - must be before any app.* imports
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
_to_remove = [k for k in list(sys.modules.keys()) if k == 'app' or k.startswith('app.')]
for k in _to_remove:
    del sys.modules[k]

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

# Backend-specific imports (from backend/app/ - these work because they're in this package)
from backend_models import Base, engine
from backend_models import *
from limiter import limiter
from routes import auth_routes, chat_routes, plan_routes, execution_routes, usage_routes, project_routes

# Now import real AI services (from project root app/)
from app.db.schema import init_db
init_db()
from app.routes.ai_memory_routes import router as ai_memory_router
from app.routes.ai_engine_routes import router as ai_engine_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Mnemosyne AI Engine")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy routes (auth, simple chat, plans)
app.include_router(auth_routes.router)
app.include_router(chat_routes.router)
app.include_router(plan_routes.router)
app.include_router(execution_routes.router)
app.include_router(usage_routes.router)
app.include_router(project_routes.router)

# Real AI engine routes
app.include_router(ai_memory_router)
app.include_router(ai_engine_router)


@app.get("/")
def root():
    return {"status": "ok", "app": "Mnemosyne AI Engine", "version": "3.0"}


@app.get("/health")
def health():
    from app.services.llm_service import LLMService
    llm = LLMService()
    return {
        "ok": True,
        "llm_provider": llm.provider,
        "llm_connected": llm.is_connected(),
    }
