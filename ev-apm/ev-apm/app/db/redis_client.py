"""
app/db/redis_client.py
======================
Redis connection for real-time alert delivery.

WHY Redis alongside PostgreSQL?
  PostgreSQL stores data. It can't "push" to connected browsers.
  Redis pub/sub is a messaging system:

    1. An alert fires (via POST /api/v1/telemetry)
    2. We INSERT the alert into PostgreSQL (permanent record)
    3. We also PUBLISH the alert to Redis channel "alerts"
    4. The WebSocket handler is subscribed to "alerts"
    5. It immediately forwards the message to all connected browsers

  Think of it as: PostgreSQL = filing cabinet, Redis = walkie-talkie.
"""

import redis.asyncio as aioredis
import json
from app.core.config import settings

_redis: aioredis.Redis = None


async def init_redis():
    """Create the Redis connection. Called once at startup."""
    global _redis
    _redis = aioredis.from_url(
        settings.REDIS_URL,
        decode_responses=True,  # return strings, not raw bytes
    )
    # Verify connection works
    await _redis.ping()
    print("✅ Redis connected")


async def get_redis() -> aioredis.Redis:
    """Returns the shared Redis client."""
    global _redis
    if _redis is None:
        await init_redis()
    return _redis


async def publish_alert(alert: dict):
    """
    Broadcasts an alert to all WebSocket clients.
    Called from the alert service after saving to PostgreSQL.

    alert: dict with vehicle_id, severity, alert_type, message, triggered_at
    """
    r = await get_redis()
    await r.publish("ev_alerts", json.dumps(alert))
