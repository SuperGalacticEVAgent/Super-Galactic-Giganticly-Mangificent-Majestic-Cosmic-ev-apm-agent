"""
app/core/config.py
==================
All configuration comes from environment variables.

WHY environment variables?
  Hard-coding passwords like DATABASE_URL = "postgresql://admin:secret@..."
  is dangerous — if you push that to GitHub, your credentials are public.
  Environment variables keep secrets OUT of your code.

  In development: create a .env file (never commit this to Git).
  In production: set these in Railway/Render dashboard.

HOW to use in code:
  from app.core.config import settings
  print(settings.DATABASE_URL)
"""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────
    # Format: postgresql://username:password@host:port/database_name
    DATABASE_URL: str = "postgresql://admin:secret@db:5432/ev_apm"

    # ── Redis (real-time alerts) ───────────────────────────
    REDIS_URL: str = "redis://localhost:6379"

    # ── Your existing ML model API ─────────────────────────
    # This is the URL of your trained ML model's prediction endpoint.
    # Example: "http://ml-model-service:8001" or "https://your-ml-api.com"
    ML_API_URL: str = "http://ml:8001"
    ML_API_KEY: str = ""          # Set this if your ML API requires authentication
    ML_TIMEOUT_SECONDS: int = 10  # How long to wait before giving up on ML response

    # ── Frontend URL (for CORS) ────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # ── Alert thresholds ──────────────────────────────────
    # These define when to trigger alerts. Adjust based on your EV specs.
    SOH_CRITICAL_THRESHOLD: float = 0.60   # below 60% → critical alert
    SOH_WARNING_THRESHOLD: float  = 0.75   # below 75% → warning alert
    TEMP_CRITICAL_CELSIUS: float  = 55.0   # above 55°C → critical alert
    TEMP_WARNING_CELSIUS: float   = 45.0   # above 45°C → warning alert
    RUL_CRITICAL_DAYS: int        = 30     # less than 30 days → critical
    RUL_WARNING_DAYS: int         = 90     # less than 90 days → warning

    class Config:
        # Automatically reads from .env file in project root
        env_file = ".env"
        env_file_encoding = "utf-8"


# Create a single instance — import this everywhere you need config
settings = Settings()
