# EV APM Agent — Backend

AI-powered Asset Performance Management backend for EV fleets. Ingests battery
telemetry, calls your trained ML model for predictions, generates alerts, and
returns charging recommendations.

## 1. Project Structure

```
ev-apm/
├── app/
│   ├── main.py                      # FastAPI app entry point
│   ├── core/
│   │   └── config.py                # Environment variable settings
│   ├── models/
│   │   └── schemas.py               # Pydantic request/response models
│   ├── db/
│   │   ├── database.py              # PostgreSQL connection + table schema
│   │   └── redis_client.py          # Redis connection for real-time alerts
│   ├── services/
│   │   ├── ml_client.py             # ★ Integration with your ML model API
│   │   ├── alert_service.py         # Threshold-based alert rule engine
│   │   └── recommendation_service.py # Charging recommendation logic
│   └── routers/
│       ├── telemetry.py             # POST /api/v1/telemetry
│       ├── predictions.py           # GET  /api/v1/predictions/{id}
│       ├── alerts.py                # GET  /api/v1/alerts + WebSocket
│       └── recommendations.py       # GET  /api/v1/recommendations/{id}
├── scripts/
│   └── test_endpoints.py            # Manual end-to-end test script
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── .gitignore
```

---

## 2. ML Integration Design

### Input parameters sent to your ML model

| Parameter | Why it's needed |
|---|---|
| `state_of_health` | Primary aging signal — the model's main target variable to forecast forward |
| `cycle_count` | Most reliable time axis for battery aging; cycles correlate directly with capacity loss |
| `avg_temperature` / `max_temperature` | Heat is the single biggest accelerant of degradation; average shows baseline stress, max shows peak thermal events |
| `soh_trend_slope` | Captures whether degradation is accelerating, not just the current snapshot |
| `dc_fast_charge_ratio` | DC fast charging causes lithium plating; this captures a key behavioral risk factor |
| `avg_discharge_current` | Higher discharge currents (aggressive driving) generate more heat and stress cells |

These are derived server-side from raw telemetry — your ML model never needs
to see raw sensor noise, just clean engineered features.

### Request format sent to your ML API (`POST {ML_API_URL}/predict`)

```json
{
  "vehicle_id": "EV-014",
  "state_of_health": 0.83,
  "cycle_count": 428,
  "avg_temperature": 36.5,
  "max_temperature": 42.1,
  "soh_trend_slope": -0.00012,
  "dc_fast_charge_ratio": 0.23,
  "avg_discharge_current": 78.4
}
```

### Response format expected from your ML API

```json
{
  "rul_days": 187,
  "soh_forecast_30d": 0.81,
  "soh_forecast_90d": 0.77,
  "degradation_rate": 1.2,
  "confidence_score": 0.91
}
```

**If your model's actual input/output field names differ**, only one file
needs to change: `app/services/ml_client.py`. Everything else in the backend
stays the same.

---

## 3. Installation & Running Locally

### Option A — Docker (recommended, no local Python/Postgres needed)

```bash
# 1. Copy environment template and fill in your ML API URL
cp .env.example .env

# 2. Start everything (Postgres + Redis + API)
docker compose up --build
```

API will be live at `http://localhost:8000`. Docs at `http://localhost:8000/docs`.

### Option B — Run locally without Docker

```bash
# 1. Install PostgreSQL and Redis locally, or use Docker just for those:
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=ev_apm -e POSTGRES_USER=admin postgres:16
docker run -d -p 6379:6379 redis:7-alpine

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Copy and edit environment variables
cp .env.example .env

# 4. Run the server
uvicorn app.main:app --reload --port 8000
```

---

## 4. Testing the Endpoints

### Option A — Interactive docs (easiest)
Open `http://localhost:8000/docs` in your browser. Every endpoint has a
"Try it out" button — no code needed.

### Option B — Test script
```bash
python scripts/test_endpoints.py
```
This sends sample telemetry, requests a prediction, and prints back
alerts and recommendations — a full smoke test in one command.

### Option C — curl examples

**Send telemetry:**
```bash
curl -X POST http://localhost:8000/api/v1/telemetry \
  -H "Content-Type: application/json" \
  -d '{
    "vehicle_id": "EV-014",
    "state_of_health": 0.83,
    "state_of_charge": 0.73,
    "cycle_count": 428,
    "battery_voltage": 396.4,
    "current_amps": -85.2,
    "temperature_cell": 38.2,
    "temperature_ambient": 31.0,
    "charge_rate_kw": 0.0,
    "is_charging": false
  }'
```
Response:
```json
{
  "status": "accepted",
  "event_id": "a1b2c3d4-...",
  "vehicle_id": "EV-014",
  "alerts_fired": 0,
  "message": "Telemetry recorded successfully"
}
```

**Get ML prediction:**
```bash
curl http://localhost:8000/api/v1/predictions/EV-014
```
Response:
```json
{
  "vehicle_id": "EV-014",
  "rul_days": 187,
  "rul_months": 6.2,
  "soh_forecast_30d": 0.81,
  "soh_forecast_90d": 0.77,
  "degradation_rate": 1.2,
  "confidence_score": 0.91,
  "prediction_note": "Generated by ML model",
  "computed_at": "2026-06-30T10:00:00Z"
}
```

**Get alerts:**
```bash
curl "http://localhost:8000/api/v1/alerts?vehicle_id=EV-014&active_only=true"
```

**Get recommendations:**
```bash
curl http://localhost:8000/api/v1/recommendations/EV-014
```

---

## 5. GitHub Repository Setup

### What to commit
Everything except what's listed in `.gitignore` — meaning all code in
`app/`, `scripts/`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`,
`.env.example`, and this `README.md`.

### What NOT to commit (`.gitignore` already covers these)
- `.env` (your real secrets — DB password, ML API key)
- `__pycache__/`, `*.pyc`
- `venv/` or `.venv/`
- IDE folders (`.vscode/`, `.idea/`)

### Suggested README sections for your repo root
1. Project title + one-line description
2. Architecture diagram or text overview
3. Setup instructions (link to this file or inline)
4. API endpoint reference table
5. Environment variables table
6. Team / contributors
7. License

---

## 6. Frontend Developer Requirements

*(No frontend code provided — these are specifications only.)*

### Pages / Screens needed

**1. Fleet Overview (`/`)**
- Grid of all vehicles with SoH badge (green/amber/red)
- Summary bar: total vehicles, active alerts, average fleet SoH
- Data source: `GET /api/v1/telemetry/{vehicle_id}/recent` per vehicle, or
  a new aggregate endpoint you may want to add (`GET /api/v1/vehicles`)

**2. Vehicle Detail (`/vehicle/[id]`)**
- SoH trend chart (line chart, last 50 readings)
- Current RUL estimate with confidence indicator
- Temperature history chart
- Active alerts for this vehicle
- Charging recommendations list
- Data sources:
  - `GET /api/v1/telemetry/{vehicle_id}/recent`
  - `GET /api/v1/predictions/{vehicle_id}`
  - `GET /api/v1/alerts?vehicle_id={id}`
  - `GET /api/v1/recommendations/{vehicle_id}`

**3. Alert Feed (`/alerts`)**
- Real-time list of all alerts across the fleet, severity-coded
- Filters: severity, vehicle, active/resolved
- Resolve button per alert
- Data sources:
  - Initial load: `GET /api/v1/alerts`
  - Real-time updates: WebSocket `ws://localhost:8000/api/v1/ws/alerts`
  - Resolve action: `PATCH /api/v1/alerts/{alert_id}/resolve`

### Components needed
- `VehicleCard` — SoH badge, status color, key stats (used in Fleet Overview)
- `SoHTrendChart` — line chart component (recharts recommended)
- `AlertBadge` — severity-colored pill (critical/warning/info)
- `AlertFeedItem` — single alert row with timestamp, message, resolve button
- `RecommendationCard` — message + charge limit + priority indicator
- `RULGauge` — visual indicator of remaining useful life (e.g. radial gauge)

### Real-time features needed
- **WebSocket connection** to `ws://localhost:8000/api/v1/ws/alerts`, opened
  once when the app loads, kept open across all pages
- New alert messages should prepend to the alert feed AND update the relevant
  vehicle's status badge color on the Fleet Overview if currently visible
- Example connection code for the frontend dev's reference:
```javascript
const ws = new WebSocket("ws://localhost:8000/api/v1/ws/alerts")
ws.onmessage = (event) => {
  const alert = JSON.parse(event.data)
  // alert = { id, vehicle_id, severity, alert_type, message, triggered_at }
}
```

---

## 7. Assumptions Made

- Your ML model API exposes a single `POST /predict` endpoint accepting and
  returning JSON (adjust `ml_client.py` if different)
- Authentication/authorization is out of scope for the hackathon version
  (no login system — add this later for production)
- A vehicle is auto-registered in the database on its first telemetry event,
  rather than requiring manual fleet setup
- DC fast charging is defined as any charge session above 22kW
- If the ML API is unreachable, a simple physics-based fallback formula is
  used so the dashboard never shows a blank/broken state
