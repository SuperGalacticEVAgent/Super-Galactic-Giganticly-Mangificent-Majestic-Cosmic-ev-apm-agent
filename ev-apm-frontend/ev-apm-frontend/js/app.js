/* =====================================================
   js/app.js  —  Shared utilities for every page.
   Include this LAST in every HTML page's <body>.
===================================================== */

// ─────────────────────────────────────────────────────
// 1. API CONFIGURATION
//    Change API_BASE_URL to point to your FastAPI backend.
//    In development: http://localhost:8000
//    In production:  https://your-railway-app.up.railway.app
// ─────────────────────────────────────────────────────
window.API_BASE_URL = 'http://localhost:8000/api/v1';
window.WS_URL       = 'ws://localhost:8000/api/v1/ws/alerts';

// ─────────────────────────────────────────────────────
// 2. API FETCH HELPER
//    Usage: const data = await api('/vehicles/EV-001/rul')
//    Automatically adds the base URL and handles errors.
// ─────────────────────────────────────────────────────
window.api = async function(path, options = {}) {
  const url = window.API_BASE_URL + path;
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return await res.json();
  } catch (e) {
    console.warn(`API call failed: ${path}`, e.message);
    throw e;
  }
};

// ─────────────────────────────────────────────────────
// 3. TOAST NOTIFICATIONS
//    Usage: toast('Vehicle connected!', 'success')
//    Types: 'success' | 'error' | 'info'
// ─────────────────────────────────────────────────────
(function setupToasts() {
  const container = document.createElement('div');
  container.id = 'toast-container';
  document.body.appendChild(container);

  window.toast = function(message, type = 'info', duration = 4000) {
    const el = document.createElement('div');
    el.className = `toast ${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => el.remove(), duration);
  };
})();

// ─────────────────────────────────────────────────────
// 4. MAGNETIC BUTTON EFFECT (optional, same as original)
// ─────────────────────────────────────────────────────
(function setupMagnetic() {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  document.querySelectorAll('.magnetic').forEach(btn => {
    btn.addEventListener('mousemove', e => {
      if (reduceMotion) return;
      const r = btn.getBoundingClientRect();
      const x = e.clientX - r.left - r.width / 2;
      const y = e.clientY - r.top - r.height / 2;
      btn.style.transform = `translate(${x * 0.18}px, ${y * 0.35}px)`;
    });
    btn.addEventListener('mouseleave', () => {
      btn.style.transform = 'translate(0,0)';
    });
  });
})();

// ─────────────────────────────────────────────────────
// 5. ACTIVE NAV LINK HIGHLIGHTING
//    Automatically marks the current page's nav link as active.
// ─────────────────────────────────────────────────────
(function highlightNav() {
  const path = window.location.pathname;
  document.querySelectorAll('.navbar-nav a').forEach(link => {
    if (link.getAttribute('href') && path.includes(link.getAttribute('href').replace('../', '').replace('./', ''))) {
      link.classList.add('active');
    }
  });
})();

// ─────────────────────────────────────────────────────
// 6. CONNECT VEHICLE MODAL
//    Opens when any element with data-open="connect-modal" is clicked.
//    3-step wizard: Enter ID → Confirm → Done
// ─────────────────────────────────────────────────────
(function setupConnectModal() {
  const overlay  = document.getElementById('connect-modal');
  if (!overlay) return;

  const closeBtn = overlay.querySelector('.modal-close');
  const steps    = overlay.querySelectorAll('.connect-step');
  const vehicleIdInput = document.getElementById('connect-vehicle-id');
  let currentStep = 0;

  // Open
  document.querySelectorAll('[data-open="connect-modal"]').forEach(btn => {
    btn.addEventListener('click', () => {
      overlay.classList.add('open');
      currentStep = 0;
      showStep(0);
      if (vehicleIdInput) vehicleIdInput.value = '';
    });
  });

  // Close
  if (closeBtn) closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeModal(); });

  // Enter key in either field submits, same as clicking Connect Vehicle
  const modelInputEl = document.getElementById('connect-vehicle-model');
  [vehicleIdInput, modelInputEl].forEach(el => {
    if (!el) return;
    el.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        const btn = document.getElementById('connect-confirm-btn');
        if (btn && !btn.disabled) btn.click();
      }
    });
  });

  function closeModal() {
    overlay.classList.remove('open');
  }

  function showStep(n) {
    steps.forEach((s, i) => s.classList.toggle('active', i === n));
    currentStep = n;
  }

  // Vehicle IDs must look like EV-001, EV-002, etc.
  const VEHICLE_ID_PATTERN = /^EV-\d{3,}$/;

  // Step 1 → 2: validate and simulate connecting
  const confirmBtn = document.getElementById('connect-confirm-btn');
  if (confirmBtn) {
    confirmBtn.addEventListener('click', async () => {
      const vehicleId = vehicleIdInput ? vehicleIdInput.value.trim() : '';
      const modelInput = document.getElementById('connect-vehicle-model');
      const vehicleModel = modelInput ? modelInput.value.trim() : '';
      if (!vehicleId) {
        toast('Please enter a Vehicle ID', 'error');
        return;
      }
      if (!VEHICLE_ID_PATTERN.test(vehicleId)) {
        toast('Vehicle ID must look like EV-001, EV-002, etc.', 'error');
        return;
      }

      confirmBtn.textContent = 'Connecting…';
      confirmBtn.disabled = true;

      try {
        // Send a first "registration" telemetry ping to the backend.
        // This auto-creates the vehicle in the database.
        // BACKEND INTEGRATION: this calls POST /api/v1/telemetry
        await window.api('/telemetry', {
          method: 'POST',
          body: JSON.stringify({
            vehicle_id:          vehicleId,
            model:               vehicleModel || undefined,
            state_of_health:     1.0,
            state_of_charge:     0.80,
            cycle_count:         0,
            battery_voltage:     400.0,
            current_amps:        0.0,
            temperature_cell:    25.0,
            temperature_ambient: 25.0,
            charge_rate_kw:      0.0,
            is_charging:         false,
            internal_resistance:  0.012,
            action_voltage:       3.70,
            action_current:       0.0,
            dT_dt:                0.0,
            dV_dt:                0.0,
            thermal_stress_index: 0.05,
            aging_indicator:      0.0,
            charging_efficiency:  0.98,
            charging_time:        0.0,
            cycle_degradation:    0.0,
            balancing_time:       0.0,
          }),
        });
        // Show success step
        const idDisplay = document.getElementById('connected-vehicle-id');
        if (idDisplay) idDisplay.textContent = vehicleId;
        showStep(1);
        toast(`Vehicle ${vehicleId} registered`, 'success');
      } catch (err) {
        // If backend not available yet, still show success (demo mode)
        const idDisplay = document.getElementById('connected-vehicle-id');
        if (idDisplay) idDisplay.textContent = vehicleId;
        showStep(1);
        toast(`${vehicleId} connected (demo mode)`, 'info');
      } finally {
        confirmBtn.textContent = 'Connect Vehicle';
        confirmBtn.disabled = false;
      }
    });
  }

  // Done button
  const doneBtn = document.getElementById('connect-done-btn');
  if (doneBtn) {
    doneBtn.addEventListener('click', () => {
      closeModal();
      const path = window.location.pathname;
      const onFleetPage = path.includes('fleet');
      const onRoot = path === '/' || path.endsWith('index.html');
      const inPagesDir = path.includes('/pages/');

      if (onFleetPage || onRoot) {
        window.location.reload();
      } else if (inPagesDir) {
        // Already inside /pages/, so fleet.html is a sibling, not 'pages/fleet.html'
        window.location.href = 'fleet.html';
      } else {
        window.location.href = 'pages/fleet.html';
      }
    });
  }
})();

// ─────────────────────────────────────────────────────
// 7. WEBSOCKET — real-time alert stream
//    Connect once; dispatches a custom "new-alert" event
//    that any page can listen to.
// ─────────────────────────────────────────────────────
(function setupWebSocket() {
  let ws, reconnectTimer;

  function connect() {
    try {
      ws = new WebSocket(window.WS_URL);

      ws.onopen = () => {
        console.log('[WS] Connected to alert stream');
      };

      ws.onmessage = (event) => {
        try {
          const alert = JSON.parse(event.data);
          // Dispatch a DOM event so any page can react
          document.dispatchEvent(new CustomEvent('new-alert', { detail: alert }));
          // Show a toast for critical alerts
          if (alert.severity === 'critical') {
            toast(`⛔ ${alert.vehicle_id}: ${alert.message}`, 'error', 6000);
          } else if (alert.severity === 'warning') {
            toast(`⚠ ${alert.vehicle_id}: ${alert.message}`, 'info', 5000);
          }
        } catch (e) {
          console.warn('[WS] Failed to parse message', e);
        }
      };

      ws.onclose = () => {
        // Reconnect after 5 seconds if connection drops
        reconnectTimer = setTimeout(connect, 5000);
      };

      ws.onerror = (e) => {
        console.warn('[WS] Connection error (backend may be offline)');
        ws.close();
      };
    } catch (e) {
      // WebSocket unavailable (backend offline in dev)
      console.warn('[WS] Could not connect to backend WebSocket');
    }
  }

  connect();
  window._alertWS = { reconnect: connect };
})();
