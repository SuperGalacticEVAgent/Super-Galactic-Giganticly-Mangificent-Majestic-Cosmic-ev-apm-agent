"""
app/routers/vehicles.py
========================
GET /api/v1/vehicles  →  one row per known vehicle, with its latest
telemetry reading and active alert count. Powers the fleet overview page.

PURELY ADDITIVE: this file only reads from tables that already exist
(vehicles, telemetry_events, alerts). It doesn't touch ml_client.py,
the ML schemas, or any other endpoint — safe to add alongside your
existing ML integration.
"""

from fastapi import APIRouter
from app.models.schemas import VehicleSummary, VehicleStatus
from app.db.database import get_pool

router = APIRouter()


@router.get("/vehicles", response_model=list[VehicleSummary])
async def list_vehicles():
    """
    For each vehicle: latest SoH/temp/SoC/cycle_count (via DISTINCT ON,
    so it's one fast query, not N+1) plus a count of unresolved alerts.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT
                v.vehicle_id,
                v.model,
                t.state_of_health  AS latest_soh,
                t.temperature_cell AS latest_temp,
                t.state_of_charge  AS latest_soc,
                t.cycle_count      AS cycle_count,
                COALESCE(a.active_alerts, 0) AS active_alerts
            FROM vehicles v
            LEFT JOIN LATERAL (
                SELECT state_of_health, temperature_cell, state_of_charge, cycle_count
                FROM telemetry_events
                WHERE vehicle_id = v.vehicle_id
                ORDER BY recorded_at DESC
                LIMIT 1
            ) t ON true
            LEFT JOIN (
                SELECT vehicle_id, COUNT(*) AS active_alerts
                FROM alerts
                WHERE resolved_at IS NULL
                GROUP BY vehicle_id
            ) a ON a.vehicle_id = v.vehicle_id
            ORDER BY v.created_at DESC
        """)

    summaries = []
    for r in rows:
        d = dict(r)
        d["status"] = _derive_status(d["latest_soh"], d["latest_temp"], d["active_alerts"])
        summaries.append(VehicleSummary(**d))
    return summaries


def _derive_status(soh, temp, active_alerts) -> VehicleStatus:
    """Simple fleet-overview status badge — mirrors the alert thresholds already in config."""
    if soh is None:
        return VehicleStatus.UNKNOWN
    if (soh is not None and soh < 0.60) or (temp is not None and temp > 55) or active_alerts >= 2:
        return VehicleStatus.CRITICAL
    if (soh is not None and soh < 0.75) or (temp is not None and temp > 45) or active_alerts >= 1:
        return VehicleStatus.WARNING
    return VehicleStatus.GOOD
