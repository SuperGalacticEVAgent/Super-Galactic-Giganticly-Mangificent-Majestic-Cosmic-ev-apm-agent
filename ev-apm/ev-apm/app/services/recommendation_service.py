"""
app/services/recommendation_service.py
=======================================
Generates charging and maintenance recommendations.

This is RULE-BASED (not ML) by design — recommendations need to be
explainable to fleet operators ("why are you telling me this?").
A simple, transparent rule set is more trustworthy than a black box
for this particular output, even though SoH/RUL prediction uses ML.
"""

from app.db.database import get_pool


async def generate_recommendations(vehicle_id: str) -> list[dict]:
    """
    Looks at recent telemetry for a vehicle and returns a prioritized
    list of recommendations. Priority 1 = most urgent.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        history = await conn.fetch("""
            SELECT state_of_health, charge_rate_kw, is_charging, temperature_cell
            FROM telemetry_events
            WHERE vehicle_id = $1
            ORDER BY recorded_at DESC
            LIMIT 100
        """, vehicle_id)

    if not history:
        return []

    rows = [dict(r) for r in history]
    soh = rows[0]["state_of_health"]

    charge_sessions = [r for r in rows if r["is_charging"]]
    dc_sessions = [r for r in charge_sessions if r["charge_rate_kw"] > 22]
    dc_ratio = len(dc_sessions) / len(charge_sessions) if charge_sessions else 0.0

    recs = []

    if soh < 0.55:
        recs.append({
            "rec_type": "replace",
            "message": "Battery is below the safe operating threshold — schedule immediate replacement",
            "charge_limit_pct": None,
            "priority": 1,
        })
    elif soh < 0.75:
        recs.append({
            "rec_type": "charge_window",
            "message": "Charge overnight (22:00–06:00) when ambient temperatures are lower — this slows further capacity loss",
            "charge_limit_pct": 80,
            "priority": 2,
        })

    if dc_ratio > 0.5:
        recs.append({
            "rec_type": "limit_dc",
            "message": f"DC fast charging used in {dc_ratio*100:.0f}% of sessions — switching to AC charging when possible will reduce wear",
            "charge_limit_pct": 80,
            "priority": 2,
        })

    if soh >= 0.75 and dc_ratio <= 0.5:
        recs.append({
            "rec_type": "maintain",
            "message": "Battery health is good — current charging habits are sustainable",
            "charge_limit_pct": 90,
            "priority": 3,
        })

    recs.sort(key=lambda r: r["priority"])
    return recs
