import joblib
import pandas as pd

from ml_config import (
    SOH_MODEL_PATH,
    ANOMALY_MODEL_PATH,
    SOH_FEATURES,
    ANOMALY_FEATURES,
)

print("Loading ML Models...")

soh_model = joblib.load(SOH_MODEL_PATH)
anomaly_model = joblib.load(ANOMALY_MODEL_PATH)

print("SOH Model Loaded Successfully!")
print("Anomaly Model Loaded Successfully!")


def predict_soh(data: dict):

    df = pd.DataFrame([[data[col] for col in SOH_FEATURES]],
                      columns=SOH_FEATURES)

    prediction = soh_model.predict(df)[0]

    return round(float(prediction), 2)


def detect_anomaly(data: dict):

    df = pd.DataFrame([[data[col] for col in ANOMALY_FEATURES]],
                      columns=ANOMALY_FEATURES)

    prediction = anomaly_model.predict(df)[0]

    if prediction == 1:
        return "Anomaly Detected"

    return "Normal"


def predict_complete(soh_data: dict, anomaly_data: dict):
    """
    Complete battery health prediction.
    Combines SOH prediction + anomaly detection + engineering estimates.
    """

    # Existing ML predictions
    predicted_soh = predict_soh(soh_data)
    anomaly_status = detect_anomaly(anomaly_data)

    # -----------------------------
    # Remaining Useful Life (RUL)
    # -----------------------------
    remaining_soh = max(predicted_soh - 60, 0)

    # Approximate degradation per day
    degradation_per_day = 0.03

    rul_days = int((remaining_soh / degradation_per_day))

    # Keep values within reasonable bounds
    rul_days = max(30, min(rul_days, 730))

    # -----------------------------
    # Forecasts
    # -----------------------------
    soh_forecast_30d = round(
        max(predicted_soh - degradation_per_day * 30, 0),
        2
    )

    soh_forecast_90d = round(
        max(predicted_soh - degradation_per_day * 90, 0),
        2
    )

    # -----------------------------
    # Confidence
    # -----------------------------
    confidence_score = 0.95

    # -----------------------------
    # Return
    # -----------------------------
    return {
        "predicted_soh": predicted_soh,
        "status": anomaly_status,
        "rul_days": rul_days,
        "soh_forecast_30d": soh_forecast_30d,
        "soh_forecast_90d": soh_forecast_90d,
        "degradation_rate": degradation_per_day,
        "confidence_score": confidence_score,
    }