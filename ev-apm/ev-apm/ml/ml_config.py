from pathlib import Path

# ============================================================
# Project Directories
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET_DIR = BASE_DIR / "dataset"
MODEL_DIR = BASE_DIR / "models"

MODEL_DIR.mkdir(exist_ok=True)

# ============================================================
# Dataset
# ============================================================

DATASET_PATH = DATASET_DIR / "battery_dataset.csv"

# ============================================================
# Model Paths
# ============================================================

SOH_MODEL_PATH = MODEL_DIR / "soh_model.pkl"
ANOMALY_MODEL_PATH = MODEL_DIR / "anomaly_model.pkl"

# ============================================================
# SOH Model Features
# ============================================================

SOH_FEATURES = [
    "state_of_charge",
    "cycle_count",
    "current_amps",
    "temperature_cell",
    "charge_rate_kw",
    "is_charging",
]

SOH_TARGET = "state_of_health"

# ============================================================
# Anomaly Model Features
# ============================================================

ANOMALY_FEATURES = [
    "internal_resistance",
    "action_voltage",
    "action_current",
    "dT_dt",
    "dV_dt",
    "thermal_stress_index",
    "aging_indicator",
    "charging_efficiency",
    "charging_time",
    "cycle_degradation",
    "balancing_time",
]

# ============================================================
# Training Settings
# ============================================================

TEST_SIZE = 0.20
RANDOM_STATE = 42