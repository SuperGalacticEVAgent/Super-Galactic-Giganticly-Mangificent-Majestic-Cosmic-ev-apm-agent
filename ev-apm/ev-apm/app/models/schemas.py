"""
app/models/schemas.py
=====================
Pydantic models define the exact shape of data flowing in and out of the API.

WHY Pydantic?
  When the simulator sends JSON to POST /api/v1/telemetry, FastAPI uses
  these models to:
    1. Parse the JSON automatically
    2. Validate every field (is state_of_health between 0 and 1?)
    3. Return a clear error message if something is wrong
    4. Auto-document the API at /docs

  Think of these as contracts: "this is exactly what I accept/return."

NAMING CONVENTION:
  - Classes ending in ...In  = what the API receives (request body)
  - Classes ending in ...Out = what the API returns (response body)
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


# ═══════════════════════════════════════════════════════════
# ENUMS — fixed set of allowed values
# ═══════════════════════════════════════════════════════════

class AlertSeverity(str, Enum):
    CRITICAL = "critical"
    WARNING  = "warning"
    INFO     = "info"


class AlertType(str, Enum):
    SOH_LOW        = "soh_low"
    THERMAL        = "thermal"
    RUL_LOW        = "rul_low"
    DC_OVERUSE     = "dc_overuse"
    RAPID_DEGRADATION = "rapid_degradation"


class RecommendationType(str, Enum):
    CHARGE_WINDOW = "charge_window"
    LIMIT_DC      = "limit_dc"
    REPLACE       = "replace"
    MAINTAIN      = "maintain"


# ═══════════════════════════════════════════════════════════
# TELEMETRY — sensor readings from vehicles
# ═══════════════════════════════════════════════════════════

class TelemetryIn(BaseModel):
    """
    Incoming telemetry event from one vehicle.
    Posted by the simulator (Person 4) every 3 seconds.

    PARAMETER DESIGN DECISIONS:
    Each parameter is chosen because it directly maps to battery degradation science.
    """

    vehicle_id: str = Field(
        ...,
        pattern=r'^EV-\d{3,}$',
        description="Unique vehicle identifier. Must look like 'EV-014' (EV- followed by 3+ digits).",
        example="EV-014"
    )

    model: Optional[str] = Field(
        default=None,
        description="Vehicle model/make, e.g. 'Tata Nexon EV'. Optional — "
                     "only used to label the vehicle in the fleet view; not used by the ML model.",
        example="Tata Nexon EV"
    )


    # ── Core battery health indicators ───────────────────────────────
    state_of_health: float = Field(
        ..., ge=0.0, le=1.0,
        description="""
        WHY: The single most important metric. SoH=1.0 means brand new battery.
        SoH=0.80 means 20% capacity has been permanently lost. Below 0.60 the
        battery should be replaced. The ML model uses this as its primary input.
        """,
        example=0.83
    )

    state_of_charge: float = Field(
        ..., ge=0.0, le=1.0,
        description="""
        WHY: Current charge level (0=empty, 1=full). Critical for RUL prediction
        because repeatedly charging to 100% or draining to 0% accelerates degradation.
        The ML model detects harmful charging patterns from SoC history.
        """,
        example=0.73
    )

    cycle_count: int = Field(
        ..., ge=0,
        description="""
        WHY: The most reliable aging counter. Every full charge-discharge cycle
        permanently degrades the battery slightly. A typical EV battery lasts
        1,000–2,000 cycles. The ML model uses this as its primary time axis for RUL.
        """,
        example=428
    )

    # ── Electrical measurements ────────────────────────────────────
    battery_voltage: float = Field(
        ..., ge=200.0, le=600.0,
        description="""
        WHY: Voltage drops as the battery ages and as cells degrade unevenly.
        Sudden voltage drops during discharge indicate cell deterioration.
        The ML model uses voltage trends to detect early degradation.
        """,
        example=396.4
    )

    current_amps: float = Field(
        ...,
        description="""
        WHY: Positive = charging, negative = discharging. The magnitude (C-rate)
        tells us how hard the battery is being pushed. High discharge currents
        (e.g. aggressive acceleration) generate more heat and degrade cells faster.
        """,
        example=-85.2
    )

    # ── Thermal measurements ───────────────────────────────────────
    temperature_cell: float = Field(
        ..., ge=-30.0, le=100.0,
        description="""
        WHY: The single biggest accelerant of battery degradation. Above 45°C
        electrolyte breakdown accelerates exponentially. The ML model uses cell
        temperature history to predict thermal-related capacity loss.
        """,
        example=38.2
    )

    temperature_ambient: float = Field(
        default=25.0,
        description="""
        WHY: Separates battery self-heating from environmental heat. If ambient
        is 40°C and cell is 42°C, that's fine. If ambient is 20°C and cell is
        55°C, the battery is generating dangerous internal heat.
        """,
        example=31.0
    )

    # ── Charging behavior ──────────────────────────────────────────
    charge_rate_kw: float = Field(
        default=0.0, ge=0.0,
        description="""
        WHY: DC fast charging (>50kW) pushes lithium ions through the electrolyte
        faster than they can intercalate cleanly, causing lithium plating —
        permanent damage. The ML model detects DC overuse patterns.
        """,
        example=0.0
    )

    is_charging: bool = Field(
        default=False,
        description="Whether the vehicle is currently plugged in and charging."
    )

    # ── Extended ML features (required by the anomaly/SoH model) ──────
    internal_resistance: float = Field(
        ..., ge=0.0,
        description="Cell internal resistance in ohms. Rises with age; a strong degradation signal.",
        example=0.015
    )

    action_voltage: float = Field(
        ...,
        description="Target/commanded per-cell voltage during the charge/discharge action.",
        example=3.80
    )

    action_current: float = Field(
        ...,
        description="Commanded current during the charge/discharge action.",
        example=20.00
    )

    dT_dt: float = Field(
        ...,
        description="Rate of change of cell temperature (deg C/s). High values indicate thermal runaway risk.",
        example=0.12
    )

    dV_dt: float = Field(
        ...,
        description="Rate of change of cell voltage (V/s). Used to detect abnormal charge/discharge behavior.",
        example=0.03
    )

    thermal_stress_index: float = Field(
        ..., ge=0.0,
        description="Composite index of accumulated thermal stress on the cell.",
        example=0.22
    )

    aging_indicator: float = Field(
        ..., ge=0.0,
        description="Composite aging signal derived from the battery's charge history.",
        example=0.08
    )

    charging_efficiency: float = Field(
        ..., ge=0.0, le=1.0,
        description="Ratio of energy delivered to energy drawn during the last charge session.",
        example=0.95
    )

    charging_time: float = Field(
        ..., ge=0.0,
        description="Duration of the last/current charging session, in seconds.",
        example=2500.0
    )

    cycle_degradation: float = Field(
        ...,
        description="Estimated capacity loss attributable to the most recent cycle.",
        example=0.00045
    )

    balancing_time: float = Field(
        ..., ge=0.0,
        description="Time spent in cell-balancing during the last charge session.",
        example=25.0
    )

    timestamp: Optional[datetime] = Field(
        default=None,
        description="Event timestamp. Defaults to server time if not provided."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_id": "EV-014",
                "state_of_health": 0.83,
                "state_of_charge": 0.73,
                "cycle_count": 428,
                "battery_voltage": 396.4,
                "current_amps": -85.2,
                "temperature_cell": 38.2,
                "temperature_ambient": 31.0,
                "charge_rate_kw": 0.0,
                "is_charging": False,
                "internal_resistance": 0.015,
                "action_voltage": 3.80,
                "action_current": 20.00,
                "dT_dt": 0.12,
                "dV_dt": 0.03,
                "thermal_stress_index": 0.22,
                "aging_indicator": 0.08,
                "charging_efficiency": 0.95,
                "charging_time": 2500.0,
                "cycle_degradation": 0.00045,
                "balancing_time": 25.0
            }
        }


class TelemetryOut(BaseModel):
    status: str = "accepted"
    event_id: str
    vehicle_id: str
    alerts_fired: int = 0
    message: str = "Telemetry recorded successfully"


# ═══════════════════════════════════════════════════════════
# ML PREDICTION — request/response with your ML model API
# ═══════════════════════════════════════════════════════════

class MLPredictionRequest(BaseModel):
    """
    What we send TO your ML model API (the FastAPI service in ml/api.py,
    running on ML_API_URL, e.g. http://localhost:8001).

    These 17 fields are exactly the flat feature set the model's
    /predict endpoint (PredictionRequest in ml/api.py) expects:
      - 6 features feed the SoH regression model
      - 11 features feed the anomaly-detection model
    vehicle_id is included for logging only; the ML service ignores it.
    """
    vehicle_id: str

    # SoH model features
    state_of_charge: float
    cycle_count: int
    current_amps: float
    temperature_cell: float
    charge_rate_kw: float
    is_charging: int

    # Anomaly model features
    internal_resistance: float
    action_voltage: float
    action_current: float
    dT_dt: float
    dV_dt: float
    thermal_stress_index: float
    aging_indicator: float
    charging_efficiency: float
    charging_time: float
    cycle_degradation: float
    balancing_time: float

    class Config:
        json_schema_extra = {
            "example": {
                "vehicle_id": "EV-014",
                "state_of_charge": 0.73,
                "cycle_count": 428,
                "current_amps": -85.2,
                "temperature_cell": 38.2,
                "charge_rate_kw": 0.0,
                "is_charging": 0,
                "internal_resistance": 0.015,
                "action_voltage": 3.80,
                "action_current": 20.00,
                "dT_dt": 0.12,
                "dV_dt": 0.03,
                "thermal_stress_index": 0.22,
                "aging_indicator": 0.08,
                "charging_efficiency": 0.95,
                "charging_time": 2500.0,
                "cycle_degradation": 0.00045,
                "balancing_time": 25.0
            }
        }


class MLPredictionResponse(BaseModel):
    """
    What your ML model API returns.

    ASSUMPTION: Your model returns these fields.
    Adjust to match your model's actual output format.
    """
    predicted_soh: float
    status: str

    rul_days: int                    # Remaining useful life in days
    soh_forecast_30d: float          # Predicted SoH in 30 days
    soh_forecast_90d: float          # Predicted SoH in 90 days
    degradation_rate: float          # % capacity lost per 100 cycles
    confidence_score: float          # Model confidence 0–1


class PredictionOut(BaseModel):
    """What we return to the frontend after getting ML model results."""
    vehicle_id: str
    rul_days: int
    rul_months: float
    soh_forecast_30d: float
    soh_forecast_90d: float
    degradation_rate: float
    confidence_score: float
    prediction_note: str
    computed_at: datetime
    predicted_soh: float
    status: str


# ═══════════════════════════════════════════════════════════
# ALERTS
# ═══════════════════════════════════════════════════════════

class AlertOut(BaseModel):
    id: str
    vehicle_id: str
    severity: AlertSeverity
    alert_type: AlertType
    message: str
    triggered_at: datetime
    resolved_at: Optional[datetime] = None


# ═══════════════════════════════════════════════════════════
# RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════

class RecommendationOut(BaseModel):
    rec_type: RecommendationType
    message: str
    charge_limit_pct: Optional[int] = None   # e.g. 80 means "charge to max 80%"
    priority: int = 3                          # 1=urgent, 2=important, 3=informational


# ═══════════════════════════════════════════════════════════
# VEHICLES — fleet overview
# ═══════════════════════════════════════════════════════════

class VehicleStatus(str, Enum):
    GOOD     = "good"
    WARNING  = "warning"
    CRITICAL = "critical"
    UNKNOWN  = "unknown"


class VehicleSummary(BaseModel):
    vehicle_id: str
    model: str
    latest_soh: Optional[float] = None
    latest_temp: Optional[float] = None
    latest_soc: Optional[float] = None
    cycle_count: Optional[int] = None
    active_alerts: int = 0
    status: VehicleStatus = VehicleStatus.UNKNOWN
