from services.ml_service import predict_soh, detect_anomaly

print("=" * 60)

# -----------------------------------
# SOH Test
# -----------------------------------

soh_input = {
    "state_of_charge": 82,
    "cycle_count": 1200,
    "current_amps": 42,
    "temperature_cell": 33,
    "charge_rate_kw": 40,
    "is_charging": 1,
}

soh = predict_soh(soh_input)

print("Predicted SOH:")
print(soh)

print()

# -----------------------------------
# Anomaly Test
# -----------------------------------

anomaly_input = {
    "internal_resistance": 0.02,
    "action_voltage": 380,
    "action_current": 42,
    "dT_dt": 0.15,
    "dV_dt": 0.01,
    "thermal_stress_index": 0.25,
    "aging_indicator": 0.30,
    "charging_efficiency": 0.95,
    "charging_time": 70,
    "cycle_degradation": 0.25,
    "balancing_time": 10,
}

status = detect_anomaly(anomaly_input)

print("Battery Status:")
print(status)

print("=" * 60)