"""
app/services/ml_client.py
=========================
Integration with your existing ML model API.

THIS IS THE KEY FILE for your use case.
Your ML model is already trained and running as a separate API.
This file handles calling it, parsing its response, and gracefully
handling errors if it's temporarily unavailable.

ASSUMPTION:
  Your ML model exposes a POST endpoint that:
  - Accepts JSON with battery features
  - Returns JSON with RUL, SoH forecast, and degradation rate

  If your ML API has a different format, only this file needs to change.
  The rest of the backend stays the same.
"""

import httpx
from typing import Optional
from app.core.config import settings
from app.models.schemas import MLPredictionRequest, MLPredictionResponse


# ──────────────────────────────────────────────────────────
# FEATURE ENGINEERING
# Converts raw telemetry history → features your ML model understands
# ──────────────────────────────────────────────────────────

def build_ml_features(vehicle_id: str, telemetry_history: list) -> MLPredictionRequest:
    """
    Takes the last N telemetry readings for a vehicle and extracts
    the flat feature set the ML API expects.

    The ML model (ml/api.py) takes the MOST RECENT reading's raw values
    directly — it doesn't need aggregate statistics, it needs the 17
    instantaneous feature values for that reading.

    IMPORTANT: The feature names here must match what your model expects
    (see ml/ml_config.py: SOH_FEATURES + ANOMALY_FEATURES).

    Args:
        vehicle_id: The vehicle identifier
        telemetry_history: List of dicts from the telemetry_events table
                           (most recent first)

    Returns:
        MLPredictionRequest ready to send to your ML API
    """
    if not telemetry_history:
        raise ValueError(f"No telemetry data available for {vehicle_id}")

    latest = telemetry_history[0]

    return MLPredictionRequest(
        vehicle_id=vehicle_id,

        # SoH model features
        state_of_charge=latest['state_of_charge'],
        cycle_count=latest['cycle_count'],
        current_amps=latest['current_amps'],
        temperature_cell=latest['temperature_cell'],
        charge_rate_kw=latest['charge_rate_kw'],
        is_charging=int(latest['is_charging']),

        # Anomaly model features
        internal_resistance=latest['internal_resistance'],
        action_voltage=latest['action_voltage'],
        action_current=latest['action_current'],
        dT_dt=latest['dt_dt'],
        dV_dt=latest['dv_dt'],
        thermal_stress_index=latest['thermal_stress_index'],
        aging_indicator=latest['aging_indicator'],
        charging_efficiency=latest['charging_efficiency'],
        charging_time=latest['charging_time'],
        cycle_degradation=latest['cycle_degradation'],
        balancing_time=latest['balancing_time'],
    )


# ──────────────────────────────────────────────────────────
# ML API CALL
# ──────────────────────────────────────────────────────────

async def call_ml_api(features: MLPredictionRequest) -> Optional[MLPredictionResponse]:
    """
    Sends features to your ML model API and returns predictions.

    Uses httpx (async HTTP client) — works with FastAPI's async model.
    Includes timeout and error handling so a slow/unavailable ML API
    doesn't crash the entire backend.

    ADJUST THIS FUNCTION to match your ML API's exact URL and format.

    Args:
        features: Prepared feature vector (from build_ml_features)

    Returns:
        MLPredictionResponse if successful, None if ML API is unavailable
    """
    headers = {"Content-Type": "application/json"}

    # Add API key if your ML model requires authentication
    if settings.ML_API_KEY:
        headers["Authorization"] = f"Bearer {settings.ML_API_KEY}"

    try:
        async with httpx.AsyncClient(timeout=settings.ML_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{settings.ML_API_URL}/predict",   # ← ADJUST THIS PATH to match your ML API
                json=features.model_dump(),
                headers=headers,
            )
            response.raise_for_status()             # raises exception for 4xx/5xx responses

            data = response.json()

            # ── Parse the response ─────────────────────────────────
            # This matches the JSON returned by ml/api.py's POST /predict
            # (see predict_complete() in ml/services/ml_service.py):
            #   { predicted_soh, status, rul_days, soh_forecast_30d,
            #     soh_forecast_90d, degradation_rate, confidence_score }
            return MLPredictionResponse(
                predicted_soh=float(data.get("predicted_soh", 0.0)),
                status=str(data.get("status", "Unknown")),
                rul_days=int(data.get("rul_days", 0)),
                soh_forecast_30d=float(data.get("soh_forecast_30d", 0.0)),
                soh_forecast_90d=float(data.get("soh_forecast_90d", 0.0)),
                degradation_rate=float(data.get("degradation_rate", 0.1)),
                confidence_score=float(data.get("confidence_score", 0.0)),
            )

    except httpx.TimeoutException:
        print(f"⚠️  ML API timeout after {settings.ML_TIMEOUT_SECONDS}s for {features.vehicle_id}")
        return None

    except httpx.HTTPStatusError as e:
        print(f"⚠️  ML API returned error {e.response.status_code}: {e.response.text}")
        return None

    except Exception as e:
        print(f"⚠️  ML API call failed: {e}")
        return None


def fallback_prediction(features: MLPredictionRequest) -> MLPredictionResponse:
    """
    Rule-based fallback used when the ML API is unavailable.

    This ensures the dashboard always shows SOMETHING rather than crashing.
    The formula is simple physics — not as accurate as your ML model, but
    gives a reasonable estimate. Uses internal_resistance and
    cycle_degradation (both proxies for aging) since we no longer have a
    directly-reported SoH to lean on here.
    """
    # Rough SoH proxy: starts near 1.0 and falls as resistance/degradation rise
    estimated_soh = max(0.5, min(1.0, 1.0 - (features.internal_resistance * 2) - (features.cycle_degradation * 100)))

    remaining_soh_to_lose = max(0.0, estimated_soh - 0.60)
    # Average degradation: ~0.0002 per cycle (rough estimate for Li-ion)
    estimated_remaining_cycles = int(remaining_soh_to_lose / 0.0002)
    # Assume ~2 cycles per day for fleet vehicles
    rul_days = max(30, int(estimated_remaining_cycles / 2))

    return MLPredictionResponse(
        predicted_soh=round(estimated_soh, 2),
        status="Unknown (fallback)",
        rul_days=min(rul_days, 730),           # cap at 2 years
        soh_forecast_30d=round(max(0.5, estimated_soh - 0.005), 3),
        soh_forecast_90d=round(max(0.5, estimated_soh - 0.015), 3),
        degradation_rate=round(features.cycle_degradation * 100, 4),  # % per 100 cycles
        confidence_score=0.0,                  # 0.0 signals "this is a fallback estimate"
    )
