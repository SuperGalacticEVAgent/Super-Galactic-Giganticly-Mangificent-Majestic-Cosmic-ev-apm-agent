"""
app/routers/telemetry.py
=========================
POST /api/v1/telemetry

The entry point for all vehicle sensor data. Whether it comes from
a real fleet or Person 4's simulator, every reading flows through here.

WHAT HAPPENS ON EACH CALL:
  1. Validate the incoming JSON (FastAPI + Pydantic do this automatically)
  2. Make sure the vehicle exists in the vehicles table (auto-create if not)
  3. Save the reading to telemetry_events
  4. Run threshold-based alert rules (fast, no ML needed)
  5. Return immediately — ML prediction happens separately (see predictions.py)

WHY split telemetry ingestion from ML prediction?
  Telemetry arrives every few seconds. Calling your ML API on every single
  reading would be slow and expensive. Instead: store fast, predict on-demand
  (or on a schedule) via the separate /predict endpoint.
"""

from fastapi import APIRouter, HTTPException
from app.models.schemas import TelemetryIn, TelemetryOut
from app.db.database import get_pool
from app.services.alert_service import run_alert_rules_for_telemetry

router = APIRouter()


@router.post("/telemetry", response_model=TelemetryOut, status_code=201)
async def ingest_telemetry(event: TelemetryIn):
    """
    Receives one telemetry reading from one vehicle and stores it.
    """
    pool = await get_pool()

    # Step 1 — make sure this vehicle exists (auto-register on first sighting)
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO vehicles (vehicle_id, model)
            VALUES ($1, COALESCE($2, 'Unknown'))
            ON CONFLICT (vehicle_id) DO NOTHING
        """, event.vehicle_id, event.model)

        # If this ping included a model name (e.g. a later correction),
        # update it — but never overwrite an existing model with nothing.
        if event.model:
            await conn.execute("""
                UPDATE vehicles SET model = $2 WHERE vehicle_id = $1
            """, event.vehicle_id, event.model)

    # Step 2 — save the telemetry reading
    async with pool.acquire() as conn:
        row = await conn.fetchrow("""
            INSERT INTO telemetry_events (
                vehicle_id, recorded_at, state_of_health, state_of_charge,
                cycle_count, battery_voltage, current_amps, temperature_cell,
                temperature_ambient, charge_rate_kw, is_charging,
                internal_resistance, action_voltage, action_current,
                dT_dt, dV_dt, thermal_stress_index, aging_indicator,
                charging_efficiency, charging_time, cycle_degradation, balancing_time
            ) VALUES ($1, COALESCE($2, NOW()), $3, $4, $5, $6, $7, $8, $9, $10, $11,
                      $12, $13, $14, $15, $16, $17, $18, $19, $20, $21, $22)
            RETURNING id
        """,
            event.vehicle_id,
            event.timestamp,
            event.state_of_health,
            event.state_of_charge,
            event.cycle_count,
            event.battery_voltage,
            event.current_amps,
            event.temperature_cell,
            event.temperature_ambient,
            event.charge_rate_kw,
            event.is_charging,
            event.internal_resistance,
            event.action_voltage,
            event.action_current,
            event.dT_dt,
            event.dV_dt,
            event.thermal_stress_index,
            event.aging_indicator,
            event.charging_efficiency,
            event.charging_time,
            event.cycle_degradation,
            event.balancing_time,
        )

    # Step 3 — run fast threshold-based alert rules
    # (these don't need the ML model — e.g. "temp > 55°C" is just a number comparison)
    alerts_fired = await run_alert_rules_for_telemetry(event)

    return TelemetryOut(
        status="accepted",
        event_id=str(row["id"]),
        vehicle_id=event.vehicle_id,
        alerts_fired=alerts_fired,
        message="Telemetry recorded successfully",
    )


@router.get("/telemetry/{vehicle_id}/recent")
async def get_recent_telemetry(vehicle_id: str, limit: int = 50):
    """
    Returns the most recent N telemetry readings for one vehicle.
    Useful for charts (SoH over time, temperature over time, etc.)
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT recorded_at, state_of_health, state_of_charge, cycle_count,
                   battery_voltage, current_amps, temperature_cell,
                   temperature_ambient, charge_rate_kw, is_charging,
                   internal_resistance, action_voltage, action_current,
                   dT_dt, dV_dt, thermal_stress_index, aging_indicator,
                   charging_efficiency, charging_time, cycle_degradation, balancing_time
            FROM telemetry_events
            WHERE vehicle_id = $1
            ORDER BY recorded_at DESC
            LIMIT $2
        """, vehicle_id, limit)

    if not rows:
        raise HTTPException(status_code=404, detail=f"No telemetry found for {vehicle_id}")

    return [dict(r) for r in rows]
