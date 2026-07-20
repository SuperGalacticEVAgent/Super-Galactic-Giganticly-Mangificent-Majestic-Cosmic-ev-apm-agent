from fastapi import FastAPI
from pydantic import BaseModel

from services.ml_service import (
    predict_soh,
    detect_anomaly,
    predict_complete
)

app = FastAPI(
    title="EV Battery ML API",
    version="1.0.0",
    description="Machine Learning API for SOH Prediction and Anomaly Detection"
)

# ==========================================================
# Request Models
# ==========================================================

class SOHRequest(BaseModel):

    state_of_charge: float
    cycle_count: int
    current_amps: float
    temperature_cell: float
    charge_rate_kw: float
    is_charging: int


class AnomalyRequest(BaseModel):

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


class PredictionRequest(BaseModel):

    # SOH Features
    state_of_charge: float
    cycle_count: int
    current_amps: float
    temperature_cell: float
    charge_rate_kw: float
    is_charging: int

    # Anomaly Features
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

# ==========================================================
# Routes
# ==========================================================

@app.get("/")
def home():

    return {
        "message": "EV Battery ML API is Running"
    }

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "models": "loaded",
        "version": "1.0.0"
    }


@app.post("/predict-soh")
def predict_soh_api(request: SOHRequest):

    result = predict_soh(request.model_dump())

    return {
        "predicted_soh": result
    }


@app.post("/detect-anomaly")
def detect_anomaly_api(request: AnomalyRequest):

    result = detect_anomaly(request.model_dump())

    return {
        "status": result
    }

@app.post("/predict")
def predict_api(request: PredictionRequest):

    data = request.model_dump()

    soh_data = {
        "state_of_charge": data["state_of_charge"],
        "cycle_count": data["cycle_count"],
        "current_amps": data["current_amps"],
        "temperature_cell": data["temperature_cell"],
        "charge_rate_kw": data["charge_rate_kw"],
        "is_charging": data["is_charging"],
    }

    anomaly_data = {
        "internal_resistance": data["internal_resistance"],
        "action_voltage": data["action_voltage"],
        "action_current": data["action_current"],
        "dT_dt": data["dT_dt"],
        "dV_dt": data["dV_dt"],
        "thermal_stress_index": data["thermal_stress_index"],
        "aging_indicator": data["aging_indicator"],
        "charging_efficiency": data["charging_efficiency"],
        "charging_time": data["charging_time"],
        "cycle_degradation": data["cycle_degradation"],
        "balancing_time": data["balancing_time"],
    }

    return predict_complete(soh_data, anomaly_data)