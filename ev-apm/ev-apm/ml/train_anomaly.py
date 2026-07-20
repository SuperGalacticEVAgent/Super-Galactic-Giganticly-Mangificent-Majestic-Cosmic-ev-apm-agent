import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from ml_config import (
    DATASET_PATH,
    ANOMALY_FEATURES,
    ANOMALY_MODEL_PATH,
    TEST_SIZE,
    RANDOM_STATE
)

print("=" * 60)
print("ANOMALY MODEL TRAINING")
print("=" * 60)

# --------------------------------------------------
# Load Dataset
# --------------------------------------------------

df = pd.read_csv(DATASET_PATH)

print("\nDataset Loaded Successfully!")
print(f"Shape : {df.shape}")

# --------------------------------------------------
# Generate Anomaly Labels
# --------------------------------------------------

def create_label(row):

    if (
        row["temperature_cell"] > 55
        or row["internal_resistance"] > 0.040
        or row["thermal_stress_index"] > 0.80
        or row["charging_efficiency"] < 0.85
    ):
        return 1

    return 0

df["anomaly"] = df.apply(create_label, axis=1)

print("\nAnomaly Distribution:")
print(df["anomaly"].value_counts())

# --------------------------------------------------
# Features & Target
# --------------------------------------------------

X = df[ANOMALY_FEATURES]
y = df["anomaly"]

# --------------------------------------------------
# Train/Test Split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE,
    stratify=y
)

# --------------------------------------------------
# Train Model
# --------------------------------------------------

print("\nTraining Anomaly Model...")

model = RandomForestClassifier(
    n_estimators=200,
    random_state=RANDOM_STATE,
    n_jobs=-1
)

model.fit(X_train, y_train)

print("Training Completed!")

# --------------------------------------------------
# Evaluate
# --------------------------------------------------

predictions = model.predict(X_test)

accuracy = accuracy_score(y_test, predictions)

print("\nModel Performance")
print("-" * 40)
print(f"Accuracy : {accuracy:.4f}")

print("\nClassification Report")
print(classification_report(y_test, predictions))

# --------------------------------------------------
# Save Model
# --------------------------------------------------

joblib.dump(model, ANOMALY_MODEL_PATH)

print("\nAnomaly Model Saved Successfully!")
print(f"Location : {ANOMALY_MODEL_PATH}")