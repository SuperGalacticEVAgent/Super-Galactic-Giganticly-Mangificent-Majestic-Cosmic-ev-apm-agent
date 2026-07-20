"""
app/routers/alerts.py
======================
GET /api/v1/alerts          → fetch alert history with filters
WS  /api/v1/ws/alerts        → real-time alert stream

HOW THE WEBSOCKET WORKS:
  Normal HTTP: browser asks → server answers → connection closes.
  WebSocket:   browser connects once → connection STAYS OPEN →
               server pushes new messages whenever it wants.

  The frontend opens ONE WebSocket connection when the dashboard loads.
  Whenever ANY vehicle triggers an alert (from telemetry or prediction),
  it's pushed through this connection instantly — no polling needed.
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from app.db.database import get_pool
from app.db.redis_client import get_redis

router = APIRouter()


@router.get("/alerts")
async def list_alerts(
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    severity: Optional[str] = Query(None, description="Filter: critical | warning | info"),
    active_only: bool = Query(True, description="Only show unresolved alerts"),
    limit: int = Query(50, le=200),
):
    """
    Fetch alert history. The frontend calls this once on page load to
    populate the initial alert feed. New alerts after that arrive via WebSocket.
    """
    pool = await get_pool()

    conditions = []
    params = []
    i = 1

    if vehicle_id:
        conditions.append(f"vehicle_id = ${i}")
        params.append(vehicle_id)
        i += 1
    if severity:
        conditions.append(f"severity = ${i}")
        params.append(severity)
        i += 1
    if active_only:
        conditions.append("resolved_at IS NULL")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT id, vehicle_id, severity, alert_type, message,
                   triggered_at, resolved_at
            FROM alerts
            {where_clause}
            ORDER BY triggered_at DESC
            LIMIT {limit}
        """, *params)

    return [dict(r) for r in rows]


@router.patch("/alerts/{alert_id}/resolve")
async def resolve_alert(alert_id: str):
    """Marks an alert as resolved — used when a fleet manager handles an issue."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            UPDATE alerts SET resolved_at = NOW()
            WHERE id = $1 AND resolved_at IS NULL
            RETURNING id
        """, alert_id)

    if not row:
        return {"status": "not_found_or_already_resolved"}
    return {"status": "resolved", "alert_id": alert_id}


@router.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket):
    """
    Real-time alert stream. Frontend connects once and receives every
    new alert as JSON text the moment it fires, for any vehicle.

    Frontend usage (JavaScript):
        const ws = new WebSocket("ws://localhost:8000/api/v1/ws/alerts")
        ws.onmessage = (event) => {
            const alert = JSON.parse(event.data)
            // prepend to alert list in UI state
        }
    """
    await websocket.accept()

    r = await get_redis()
    pubsub = r.pubsub()
    await pubsub.subscribe("ev_alerts")

    try:
        async for message in pubsub.listen():
            # Redis sends a "subscribe" confirmation message first — skip it.
            # Only forward actual published alerts (type == "message").
            if message["type"] == "message":
                await websocket.send_text(message["data"])

    except WebSocketDisconnect:
        await pubsub.unsubscribe("ev_alerts")
    except Exception as e:
        print(f"WebSocket error: {e}")
        await pubsub.unsubscribe("ev_alerts")
