import joblib
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score
)
from sklearn.model_selection import train_test_split

from ml_config import (
    DATASET_PATH,
    SOH_FEATURES,
    SOH_TARGET,
    SOH_MODEL_PATH,
    TEST_SIZE,
    RANDOM_STATE
)

print("=" * 60)
print("SOH MODEL TRAINING")
print("=" * 60)

# --------------------------------------------------
# Load Dataset
# --------------------------------------------------

df = pd.read_csv(DATASET_PATH)

print("\nDataset Loaded Successfully!")
print(f"Shape : {df.shape}")

# --------------------------------------------------
# Select Features and Target
# --------------------------------------------------

X = df[SOH_FEATURES]
y = df[SOH_TARGET]

print("\nFeatures:")
print(SOH_FEATURES)

print("\nTarget:")
print(SOH_TARGET)

# --------------------------------------------------
# Train/Test Split
# --------------------------------------------------

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=TEST_SIZE,
    random_state=RANDOM_STATE
)

print(f"\nTraining Samples : {len(X_train)}")
print(f"Testing Samples  : {len(X_test)}")

# --------------------------------------------------
# Train Model
# --------------------------------------------------

print("\nTraining SOH Model...")

model = RandomForestRegressor(
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

mae = mean_absolute_error(y_test, predictions)
mse = mean_squared_error(y_test, predictions)
rmse = mse ** 0.5
r2 = r2_score(y_test, predictions)

print("\nModel Performance")
print("-" * 40)
print(f"MAE  : {mae:.4f}")
print(f"RMSE : {rmse:.4f}")
print(f"R²   : {r2:.4f}")

# --------------------------------------------------
# Save Model
# --------------------------------------------------

joblib.dump(model, SOH_MODEL_PATH)

print("\nSOH Model Saved Successfully!")
print(f"Location : {SOH_MODEL_PATH}")