"""
scripts/test_endpoints.py
==========================
A simple script to manually test every endpoint end-to-end.
Run this AFTER starting the server (uvicorn app.main:app --reload).

Usage:
    python scripts/test_endpoints.py
"""

import httpx
import time

BASE_URL = "http://localhost:8000/api/v1"
VEHICLE_ID = "EV-TEST-01"


def main():
    client = httpx.Client(timeout=15)

    print("1. Sending telemetry...")
    telemetry_payload = {
        "vehicle_id": VEHICLE_ID,
        "state_of_health": 0.58,        # intentionally low — should trigger an alert
        "state_of_charge": 0.65,
        "cycle_count": 612,
        "battery_voltage": 380.5,
        "current_amps": -70.2,
        "temperature_cell": 47.0,        # intentionally elevated — should trigger an alert
        "temperature_ambient": 30.0,
        "charge_rate_kw": 0.0,
        "is_charging": False,
    }
    r = client.post(f"{BASE_URL}/telemetry", json=telemetry_payload)
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}\n")

    # Send a few more readings so the ML feature builder has history to work with
    print("2. Sending 5 more telemetry readings for history...")
    for i in range(5):
        telemetry_payload["state_of_health"] -= 0.001
        telemetry_payload["cycle_count"] += 1
        client.post(f"{BASE_URL}/telemetry", json=telemetry_payload)
        time.sleep(0.2)
    print("   Done\n")

    print("3. Fetching recent telemetry...")
    r = client.get(f"{BASE_URL}/telemetry/{VEHICLE_ID}/recent?limit=5")
    print(f"   Status: {r.status_code}")
    print(f"   Rows returned: {len(r.json())}\n")

    print("4. Requesting ML prediction...")
    r = client.get(f"{BASE_URL}/predictions/{VEHICLE_ID}")
    print(f"   Status: {r.status_code}")
    print(f"   Response: {r.json()}\n")

    print("5. Fetching alerts...")
    r = client.get(f"{BASE_URL}/alerts?vehicle_id={VEHICLE_ID}")
    print(f"   Status: {r.status_code}")
    print(f"   Alerts found: {len(r.json())}")
    for alert in r.json():
        print(f"      [{alert['severity']}] {alert['message']}")
    print()

    print("6. Fetching recommendations...")
    r = client.get(f"{BASE_URL}/recommendations/{VEHICLE_ID}")
    print(f"   Status: {r.status_code}")
    print(f"   Recommendations: {r.json()}\n")

    print("✅ All endpoints tested. Check output above for any errors.")


if __name__ == "__main__":
    main()
