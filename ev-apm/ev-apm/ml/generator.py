import random
import pandas as pd
import os

NUM_RECORDS = 20000

data = []

for _ in range(NUM_RECORDS):

    # -----------------------------
    # SOH Features
    # -----------------------------

    cycle_count = random.randint(0,3500)

    state_of_charge = round(random.uniform(10,100),2)

    current_amps = round(random.uniform(5,250),2)

    temperature_cell = round(random.uniform(20,65),2)

    charge_rate_kw = round(random.uniform(3,150),2)

    is_charging = random.choice([0,1])

    # -----------------------------
    # Anomaly Features
    # -----------------------------

    internal_resistance = round(random.uniform(0.005,0.05),4)

    action_voltage = round(random.uniform(300,450),2)

    action_current = round(random.uniform(10,250),2)

    dT_dt = round(random.uniform(-0.5,1.5),3)

    dV_dt = round(random.uniform(-0.05,0.05),4)

    charging_efficiency = round(random.uniform(0.80,0.99),3)

    charging_time = round(random.uniform(15,180),2)

    balancing_time = round(random.uniform(0,30),2)

    cycle_degradation = round(cycle_count * 0.00025,4)

    thermal_stress_index = round(
        (temperature_cell/65)*0.6 + abs(dT_dt)*0.4,
        3
    )

    aging_indicator = round(
        (cycle_count/3500),
        3
    )

    # -----------------------------
    # Calculate SOH
    # -----------------------------

    soh = 100

    soh -= cycle_count * 0.008

    soh -= max(0,temperature_cell-35)*0.30

    soh -= internal_resistance*200

    soh += charging_efficiency*3

    soh = max(40,min(100,round(soh,2)))

    data.append({

        "state_of_health":soh,

        "state_of_charge":state_of_charge,
        "cycle_count":cycle_count,
        "current_amps":current_amps,
        "temperature_cell":temperature_cell,
        "charge_rate_kw":charge_rate_kw,
        "is_charging":is_charging,

        "internal_resistance":internal_resistance,
        "action_voltage":action_voltage,
        "action_current":action_current,
        "dT_dt":dT_dt,
        "dV_dt":dV_dt,
        "thermal_stress_index":thermal_stress_index,
        "aging_indicator":aging_indicator,
        "charging_efficiency":charging_efficiency,
        "charging_time":charging_time,
        "cycle_degradation":cycle_degradation,
        "balancing_time":balancing_time

    })

df = pd.DataFrame(data)

os.makedirs("dataset",exist_ok=True)

df.to_csv("dataset/battery_dataset.csv",index=False)

print(df.head())

print()

print("Dataset Shape :",df.shape)

print("Dataset Saved Successfully!")