"""
app/main.py
===========
Entry point for the EV APM FastAPI backend.

Run with:
    uvicorn app.main:app --reload

Then open: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.database import create_tables
from app.db.redis_client import init_redis
from app.routers import telemetry, predictions, alerts, recommendations, vehicles
from app.core.config import settings


# ─────────────────────────────────────────────────────────
# LIFESPAN: code here runs ONCE at startup and shutdown.
# Use it for: DB setup, loading models, opening connections.
# ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("🔌 Setting up database tables...")
    await create_tables()

    print("📡 Connecting to Redis...")
    await init_redis()

    print("✅ Backend is ready!")
    yield  # <-- app runs while we're here

    # --- SHUTDOWN ---
    print("👋 Server shutting down.")


# ─────────────────────────────────────────────────────────
# CREATE THE APP
# ─────────────────────────────────────────────────────────
app = FastAPI(
    title="EV APM Agent API",
    description="Battery health monitoring and predictive maintenance for EV fleets",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the Next.js frontend (port 3000) to call this API (port 8000).
# Without CORS, browsers block requests between different ports/domains.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────
# REGISTER ROUTERS
# Each router lives in its own file and handles a group of endpoints.
# The prefix means: telemetry.router endpoints become /api/v1/telemetry/...
# ─────────────────────────────────────────────────────────
app.include_router(telemetry.router,       prefix="/api/v1", tags=["Telemetry"])
app.include_router(predictions.router,     prefix="/api/v1", tags=["ML Predictions"])
app.include_router(alerts.router,          prefix="/api/v1", tags=["Alerts"])
app.include_router(recommendations.router, prefix="/api/v1", tags=["Recommendations"])
app.include_router(vehicles.router,        prefix="/api/v1", tags=["Vehicles"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Quick check that the server is running. Used by Docker and monitoring."""
    return {"status": "ok", "version": "1.0.0"}
