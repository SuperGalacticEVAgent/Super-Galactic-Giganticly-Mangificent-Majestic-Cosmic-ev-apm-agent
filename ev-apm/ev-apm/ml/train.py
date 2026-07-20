from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.model_selection import train_test_split
import pandas as pd
import joblib

from ml_config import DATASET_DIR, SYNTHETIC_SOH_FEATURES, SYNTHETIC_SOH_MODEL_PATH


# ----------------------------------
# Load Dataset
# ----------------------------------
print("=" * 50)
print("EV Asset Performance Management")
print("Machine Learning Training")
print("=" * 50)

df = pd.read_csv(
    DATASET_DIR / "ev_dataset.csv",
    keep_default_na=False
)

# ----------------------------------
# Basic Information
# ----------------------------------
print("\nDataset Loaded Successfully!")

print("\nDataset Shape:")
print(df.shape)

print("\nColumns:")
for column in df.columns:
    print(f"- {column}")

print("\nData Types:")
print(df.dtypes)

print("\nMissing Values:")
print(df.isnull().sum())

print("\nFirst Five Rows:")
print(df.head())
# ----------------------------------
# Feature Selection
# ----------------------------------

features = SYNTHETIC_SOH_FEATURES

target = "soh"

X = df[features]
y = df[target]

print("\nFeatures Selected:")
print(features)

print("\nTarget:")
print(target)

print("\nShape of X:", X.shape)
print("Shape of y:", y.shape)

# ----------------------------------
# Train-Test Split
# ----------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("\nTraining Samples:", len(X_train))
print("Testing Samples:", len(X_test))
# ----------------------------------
# Train Random Forest Model
# ----------------------------------

print("\nTraining Random Forest Model...")

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X_train, y_train)

print("Model Training Completed!")

# ----------------------------------
# Predictions
# ----------------------------------

y_pred = model.predict(X_test)

# ----------------------------------
# Model Evaluation
# ----------------------------------

mae = mean_absolute_error(y_test, y_pred)

mse = mean_squared_error(y_test, y_pred)

rmse = mse ** 0.5

r2 = r2_score(y_test, y_pred)

print("\nModel Performance")

print("-" * 30)

print(f"MAE  : {mae:.2f}")

print(f"RMSE : {rmse:.2f}")

print(f"R² Score : {r2:.4f}")

# ----------------------------------
# Save Model
# ----------------------------------

joblib.dump(
    model,
    SYNTHETIC_SOH_MODEL_PATH
)

print("\nSOH Model Saved Successfully!")
print("Location: models/soh_model.pkl")
