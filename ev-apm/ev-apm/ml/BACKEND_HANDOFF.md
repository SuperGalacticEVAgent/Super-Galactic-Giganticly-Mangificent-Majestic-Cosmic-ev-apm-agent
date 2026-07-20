# ML Model Backend Handoff

This folder contains the EV battery ML models and Python helper functions for backend integration.

## Setup

Create a Python environment and install dependencies:

```bash
pip install -r requirements.txt
```

## Quick Test

From this `ml` folder, run:

```bash
python predict.py
```

You should see a predicted SOH value and battery anomaly status.

## Backend Usage

Import the model functions:

```python
from services.ml_service import predict_soh, predict_real_soh, detect_anomaly
```

### Synthetic SOH Model

Use `predict_soh(vehicle_data)` for the synthetic/demo SOH model.

Required fields:

```python
vehicle_data = {
    "voltage": 398.75,
    "current": 82.50,
    "battery_temperature": 35.20,
    "ambient_temperature": 29.10,
    "soc": 78.60,
    "charge_cycles": 640,
    "battery_capacity": 75,
    "speed": 58.40,
    "distance": 18250.75,
    "power": 32.90,
    "voltage_imbalance": 0.042,
}

soh = predict_soh(vehicle_data)
```

### Real Dataset SOH Model

Use `predict_real_soh(vehicle_data)` for the model trained on `nev_battery_charging.csv`.

Required fields:

```python
vehicle_data = {
    "SOC": 0.75,
    "terminal_voltage": 3.72,
    "battery_current": 18.50,
    "battery_temp": 32.00,
    "ambient_temp": 27.50,
    "internal_resistance": 0.015,
    "action_current": 20.00,
    "action_voltage": 3.80,
    "dT_dt": 0.12,
    "dV_dt": 0.03,
    "thermal_stress_index": 0.22,
    "aging_indicator": 0.08,
    "charging_efficiency": 0.95,
    "charging_time": 2500,
    "cycle_degradation": 0.00045,
    "balancing_time": 25.0,
}

soh = predict_real_soh(vehicle_data)
```

### Anomaly Model

Use `detect_anomaly(vehicle_data)`.

Required fields:

```python
vehicle_data = {
    "terminal_voltage": 3.72,
    "battery_current": 18.50,
    "battery_temp": 32.00,
    "ambient_temp": 27.50,
    "internal_resistance": 0.015,
    "action_current": 20.00,
    "action_voltage": 3.80,
    "dT_dt": 0.12,
    "dV_dt": 0.03,
    "thermal_stress_index": 0.22,
    "charging_efficiency": 0.95,
    "cycle_degradation": 0.00045,
}

status = detect_anomaly(vehicle_data)
```

Return value is either:

```text
Normal
Anomaly Detected
```

## Important Notes

- Keep the `models/` folder with the Python files. The `.pkl` files are required for prediction.
- Do not rename model files unless you also update `ml_config.py`.
- `venv/` is not included in the handoff zip. Create a fresh environment on the backend machine.
- `evaluate.py` can be used to check model metrics:

```bash
python evaluate.py
```
