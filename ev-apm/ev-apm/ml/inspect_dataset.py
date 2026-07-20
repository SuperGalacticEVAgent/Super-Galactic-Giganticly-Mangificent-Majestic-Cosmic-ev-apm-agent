import pandas as pd

# Load the real dataset
df = pd.read_csv("dataset/nev_battery_charging.csv")

print("=" * 50)
print("REAL EV DATASET")
print("=" * 50)

print("\nShape:")
print(df.shape)

print("\nColumns:")
print(df.columns.tolist())

print("\nData Types:")
print(df.dtypes)

print("\nMissing Values:")
print(df.isnull().sum())

print("\nFirst Five Rows:")
print(df.head())

print("\nDataset Statistics:")
print(df.describe())