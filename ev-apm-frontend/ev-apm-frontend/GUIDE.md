# EV APM Frontend — Complete Guide

## File Structure

```
ev-apm-frontend/
├── index.html              ← Home / landing page
├── css/
│   └── styles.css          ← All shared styles (imported by every page)
├── js/
│   └── app.js              ← Shared JS: API config, toasts, WebSocket, modal
└── pages/
    ├── fleet.html          ← Fleet overview with live voltage/SoC cards
    ├── alerts.html         ← Real-time alert feed (WebSocket)
    ├── predictions.html    ← ML prediction results per vehicle
    └── dashboard.html      ← Operator console with charts
```

---

## 1. How to Run Locally (without a web server)

Just open `index.html` in your browser:
  - Double-click the file in your file explorer, OR
  - Drag it into Chrome/Firefox

The pages work standalone with demo data when the backend is offline.

**Better option — use a local server** (avoids some browser quirks):

```bash
# If you have Python installed:
cd ev-apm-frontend
python3 -m http.server 3000
# Then open: http://localhost:3000
```

```bash
# If you have Node.js installed:
npx serve ev-apm-frontend
# Then open the URL it shows you
```

---

## 2. How to Connect Your FastAPI Backend

Open `js/app.js` and change these two lines at the top:

```javascript
// BEFORE (development):
window.API_BASE_URL = 'http://localhost:8000/api/v1';
window.WS_URL       = 'ws://localhost:8000/api/v1/ws/alerts';

// AFTER (your deployed backend on Railway):
window.API_BASE_URL = 'https://your-app.up.railway.app/api/v1';
window.WS_URL       = 'wss://your-app.up.railway.app/api/v1/ws/alerts';
```

That's the ONLY change needed to point the frontend at any backend URL.

---

## 3. Replacing Placeholder Metrics with Real Backend Data

Every place where demo data is used is marked with a comment:
  `// BACKEND INTEGRATION:`

Here's a summary of what each page calls and what to change:

### fleet.html — Vehicle Table
```javascript
// CURRENTLY: uses hardcoded demo vehicles array
// REPLACE WITH:
const vehicles = await api('/vehicles');
// Requires adding GET /api/v1/vehicles to your FastAPI backend
// Should return array of { vehicle_id, model, latest_soh, battery_voltage, temperature_cell, cycle_count, active_alerts }
```

### fleet.html — Live Voltage / SoC cards
```javascript
// CURRENTLY: calls GET /api/v1/telemetry/{vehicle_id}/recent?limit=1
// This ALREADY works with your backend — no change needed
// Just make sure the vehicle_id exists (connect a vehicle first)
```

### dashboard.html — Fleet Avg Voltage / SoC
```javascript
// CURRENTLY: polls GET /api/v1/telemetry/EV-001/recent?limit=1
// CHANGE 'EV-001' to a real vehicle ID from your fleet:
const data = await api('/telemetry/YOUR-VEHICLE-ID/recent?limit=1');

// BETTER: add a fleet summary endpoint to the backend:
// GET /api/v1/fleet/summary → { avg_soh, avg_voltage, avg_soc, total_vehicles, active_alerts }
```

### alerts.html — Alert feed
```javascript
// ALREADY works with backend — calls:
// GET /api/v1/alerts?active_only=true&limit=50
// PATCH /api/v1/alerts/{id}/resolve
// ws://localhost:8000/api/v1/ws/alerts  (real-time)
```

### predictions.html — ML results
```javascript
// ALREADY works with backend — calls:
// GET /api/v1/predictions/{vehicle_id}  → triggers your ML model
// GET /api/v1/recommendations/{vehicle_id}
```

---

## 4. Hosting the Website

### Option A — GitHub Pages (free, no backend needed for the demo UI)

1. Create a GitHub repository
2. Upload all the frontend files (index.html, css/, js/, pages/)
3. Go to Settings → Pages → Source: main branch / root
4. Your site will be live at: `https://yourusername.github.io/your-repo/`

**Important**: Update `js/app.js` with your deployed backend URL before pushing.

### Option B — Netlify (free, one drag-and-drop)

1. Go to netlify.com → New site → Drag and drop your `ev-apm-frontend` folder
2. Done — live URL in 30 seconds
3. Update `js/app.js` with your backend URL, push changes → auto-deploys

### Option C — Serve from your FastAPI backend (everything on one server)

Add this to your `app/main.py`:

```python
from fastapi.staticfiles import StaticFiles

# Mount the frontend folder
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
```

Then put your frontend files in a `frontend/` folder inside the backend repo.
Run `uvicorn app.main:app` and visit `http://localhost:8000` — you'll see
the frontend AND the API at `/api/v1/...` on the same server.

Change `js/app.js` to use relative URLs:
```javascript
window.API_BASE_URL = '/api/v1';
window.WS_URL       = `ws://${location.host}/api/v1/ws/alerts`;
```

This is the cleanest setup for Railway deployment — one service, one URL.

---

## 5. CORS — Making Backend Accept Frontend Requests

If your frontend is on a different domain than your backend (e.g. Netlify
frontend + Railway backend), you MUST tell the backend to allow it.

In your `app/core/config.py`:
```python
CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "https://your-site.netlify.app",   # ← add your frontend URL
    "https://yourusername.github.io",   # ← or GitHub Pages URL
]
```

Without this, the browser will block API calls with a CORS error.

---

## 6. Summary — What Each File Does

| File | Purpose |
|---|---|
| `index.html` | Landing page with globe animation and module quick links |
| `pages/fleet.html` | Vehicle table + live voltage/SoC cards that poll every 5s |
| `pages/alerts.html` | Alert history + WebSocket real-time feed + resolve button |
| `pages/predictions.html` | Calls ML model per vehicle, shows RUL + SoH forecast bars |
| `pages/dashboard.html` | Operator console with degradation chart + live metrics |
| `css/styles.css` | ALL styles shared across every page — edit here for global look |
| `js/app.js` | API URL config, `api()` fetch helper, toast notifications, WebSocket, Connect Vehicle modal |
