from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import agents, monitor, redteam, health, incidents, webhooks, tenants, metrics, auth, workspace, analytics, logs, keys, notifications, llm_models
from app.db.events import init_db

app = FastAPI(title=settings.PROJECT_NAME, openapi_url=f"{settings.API_V1_STR}/openapi.json")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Local Vite dev
        "http://localhost:8080",  # Local alternative
        "https://veridian-ai-1.netlify.app",  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup():
    await init_db()

app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(workspace.router, prefix="/workspace", tags=["workspace"])
app.include_router(agents.router, prefix=f"{settings.API_V1_STR}/agents", tags=["agents"])
app.include_router(monitor.router, prefix=f"{settings.API_V1_STR}/monitor", tags=["monitor"])
app.include_router(redteam.router, prefix=f"{settings.API_V1_STR}/redteam", tags=["redteam"])
app.include_router(incidents.router, prefix=f"{settings.API_V1_STR}/incidents", tags=["incidents"])
app.include_router(webhooks.router, prefix=f"{settings.API_V1_STR}/webhook", tags=["webhooks"])
app.include_router(tenants.router, prefix=f"{settings.API_V1_STR}/tenants", tags=["tenants"])
app.include_router(metrics.router, prefix=f"{settings.API_V1_STR}/metrics", tags=["metrics"])
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])
app.include_router(keys.router, prefix=f"{settings.API_V1_STR}/keys", tags=["keys"])
app.include_router(notifications.router, prefix=f"{settings.API_V1_STR}/notifications", tags=["notifications"])
app.include_router(llm_models.router, prefix=f"{settings.API_V1_STR}/models", tags=["models"])

@app.get("/")
async def root():
    return {"message": "Welcome to AI Sentinel API"}
