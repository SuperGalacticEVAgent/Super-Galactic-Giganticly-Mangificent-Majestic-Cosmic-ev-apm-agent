"""
app/services/alert_service.py
==============================
The alert rule engine. Runs after every telemetry event AND after
every ML prediction, checking values against thresholds.

DEDUPLICATION:
  The simulator sends data every few seconds. Without deduplication,
  one vehicle with low SoH would fire hundreds of identical alerts
  per hour, flooding the dashboard. We only fire each (vehicle, alert_type)
  combination once per hour.
"""

import json
from app.db.database import get_pool
from app.db.redis_client import publish_alert
from app.core.config import settings


# ──────────────────────────────────────────────────────────
# RULES BASED ON RAW TELEMETRY
# Each rule: (condition function, alert_type, severity, message builder)
# ──────────────────────────────────────────────────────────

def _telemetry_rules(event):
    return [
        (event.state_of_health < settings.SOH_CRITICAL_THRESHOLD,
         "soh_low", "critical",
         f"State of health dropped to {event.state_of_health*100:.0f}% — schedule replacement"),

        (event.state_of_health < settings.SOH_WARNING_THRESHOLD,
         "soh_low", "warning",
         f"State of health at {event.state_of_health*100:.0f}% — monitor closely"),

        (event.temperature_cell > settings.TEMP_CRITICAL_CELSIUS,
         "thermal", "critical",
         f"Cell temperature {event.temperature_cell:.1f}°C — thermal runaway risk"),

        (event.temperature_cell > settings.TEMP_WARNING_CELSIUS,
         "thermal", "warning",
         f"Elevated cell temperature: {event.temperature_cell:.1f}°C"),

        (event.is_charging and event.charge_rate_kw > 50,
         "dc_overuse", "info",
         f"DC fast charging at {event.charge_rate_kw:.0f}kW — frequent fast charging accelerates wear"),
    ]


def _ml_prediction_rules(vehicle_id: str, prediction):
    return [
        (prediction.rul_days < settings.RUL_CRITICAL_DAYS,
         "rul_low", "critical",
         f"Remaining useful life only {prediction.rul_days} days — plan replacement now"),

        (prediction.rul_days < settings.RUL_WARNING_DAYS,
         "rul_low", "warning",
         f"Remaining useful life is {prediction.rul_days} days — start budgeting for replacement"),

        (prediction.degradation_rate > 2.0,
         "rapid_degradation", "warning",
         f"Degradation rate of {prediction.degradation_rate:.1f}%/100 cycles is faster than normal"),
    ]


# ──────────────────────────────────────────────────────────
# PUBLIC FUNCTIONS — called from routers
# ──────────────────────────────────────────────────────────

async def run_alert_rules_for_telemetry(event) -> int:
    """Evaluates threshold rules against a raw telemetry event. Returns count fired."""
    fired = 0
    for condition, alert_type, severity, message in _telemetry_rules(event):
        if condition:
            if await _maybe_fire_alert(event.vehicle_id, alert_type, severity, message):
                fired += 1
    return fired


async def run_alert_rules_for_prediction(vehicle_id: str, prediction) -> int:
    """Evaluates threshold rules against an ML prediction result. Returns count fired."""
    fired = 0
    for condition, alert_type, severity, message in _ml_prediction_rules(vehicle_id, prediction):
        if condition:
            if await _maybe_fire_alert(vehicle_id, alert_type, severity, message):
                fired += 1
    return fired


async def _maybe_fire_alert(vehicle_id: str, alert_type: str, severity: str, message: str) -> bool:
    """
    Inserts an alert ONLY if no identical (vehicle, alert_type) alert
    fired within the last hour. Returns True if a new alert was fired.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:

        existing = await conn.fetchrow("""
            SELECT id FROM alerts
            WHERE vehicle_id   = $1
              AND alert_type   = $2
              AND resolved_at IS NULL
              AND triggered_at > NOW() - INTERVAL '1 hour'
        """, vehicle_id, alert_type)

        if existing:
            return False  # already alerted recently, skip

        row = await conn.fetchrow("""
            INSERT INTO alerts (vehicle_id, severity, alert_type, message)
            VALUES ($1, $2, $3, $4)
            RETURNING id, triggered_at
        """, vehicle_id, severity, alert_type, message)

    # Push to Redis so any open WebSocket connections get it instantly
    await publish_alert({
        "id":           str(row["id"]),
        "vehicle_id":   vehicle_id,
        "severity":     severity,
        "alert_type":   alert_type,
        "message":      message,
        "triggered_at": row["triggered_at"].isoformat(),
    })

    return True
