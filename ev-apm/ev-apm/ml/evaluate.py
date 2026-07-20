import joblib
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from ml_config import (
    ANOMALY_FEATURES,
    ANOMALY_MODEL_PATH,
    DATASET_DIR,
    REAL_SOH_FEATURES,
    REAL_SOH_MODEL_PATH,
    SYNTHETIC_SOH_FEATURES,
    SYNTHETIC_SOH_MODEL_PATH,
)


def evaluate_regression_model(name, dataset_path, model_path, features, target):
    df = pd.read_csv(dataset_path)
    model = joblib.load(model_path)

    _, X_test, _, y_test = train_test_split(
        df[features],
        df[target],
        test_size=0.2,
        random_state=42,
    )

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)

    print(f"\n{name}")
    print("-" * len(name))
    print(f"Rows        : {len(df)}")
    print(f"MAE         : {mean_absolute_error(y_test, y_pred):.6f}")
    print(f"RMSE        : {mse ** 0.5:.6f}")
    print(f"R2          : {r2_score(y_test, y_pred):.6f}")


def evaluate_anomaly_model():
    df = pd.read_csv(DATASET_DIR / "nev_battery_charging.csv")
    model = joblib.load(ANOMALY_MODEL_PATH)

    predictions = model.predict(df[ANOMALY_FEATURES])
    anomaly_count = int((predictions == -1).sum())
    normal_count = int((predictions == 1).sum())

    print("\nAnomaly Model")
    print("-------------")
    print(f"Rows        : {len(df)}")
    print(f"Normal      : {normal_count}")
    print(f"Anomalies   : {anomaly_count}")
    print(f"Anomaly %   : {(anomaly_count / len(df)) * 100:.2f}%")


def main():
    print("=" * 60)
    print("ML MODEL EVALUATION")
    print("=" * 60)

    evaluate_regression_model(
        name="Synthetic SOH Model",
        dataset_path=DATASET_DIR / "ev_dataset.csv",
        model_path=SYNTHETIC_SOH_MODEL_PATH,
        features=SYNTHETIC_SOH_FEATURES,
        target="soh",
    )

    evaluate_regression_model(
        name="Real SOH Model",
        dataset_path=DATASET_DIR / "nev_battery_charging.csv",
        model_path=REAL_SOH_MODEL_PATH,
        features=REAL_SOH_FEATURES,
        target="SOH",
    )

    evaluate_anomaly_model()


if __name__ == "__main__":
    main()
