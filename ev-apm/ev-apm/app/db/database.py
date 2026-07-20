"""
app/db/database.py
==================
Handles the PostgreSQL connection and creates all tables.

WHY asyncpg over regular psycopg2?
  FastAPI handles many requests at the same time (asynchronously).
  Regular psycopg2 BLOCKS the entire server while waiting for a DB query.
  asyncpg doesn't block — it lets other requests run while waiting for DB.

CONNECTION POOL:
  Instead of opening and closing a DB connection for every single request
  (expensive), we keep a "pool" of 2–10 connections open and reuse them.
  This is standard practice for any production web app.
"""

import asyncpg
from app.core.config import settings

# Global pool — created once at startup, shared across all requests
_pool: asyncpg.Pool = None


async def get_pool() -> asyncpg.Pool:
    """Returns the shared connection pool. Initialize if not yet created."""
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=2,    # always keep 2 connections open
            max_size=10,   # never open more than 10 at once
        )
    return _pool


async def create_tables():
    """
    Creates all database tables if they don't already exist.
    Called once at startup — safe to run multiple times.

    THIS IS YOUR DATABASE SCHEMA.
    Think of each CREATE TABLE block as designing a spreadsheet:
    the column names, types, and constraints are all defined here.
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""

            -- ──────────────────────────────────────────────────────
            -- VEHICLES TABLE
            -- One row per physical EV. Master reference for all data.
            -- ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS vehicles (
                id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id  TEXT        UNIQUE NOT NULL,
                model       TEXT        NOT NULL DEFAULT 'Unknown',
                fleet_id    TEXT        DEFAULT 'default',
                created_at  TIMESTAMPTZ DEFAULT NOW()
            );

            -- ──────────────────────────────────────────────────────
            -- TELEMETRY_EVENTS TABLE
            -- One row per sensor reading. High-volume — can grow to
            -- millions of rows. Indexed for fast vehicle+time queries.
            -- ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS telemetry_events (
                id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id          TEXT        NOT NULL REFERENCES vehicles(vehicle_id),
                recorded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                state_of_health     FLOAT       NOT NULL,
                state_of_charge     FLOAT       NOT NULL,
                cycle_count         INTEGER     NOT NULL,
                battery_voltage     FLOAT,
                current_amps        FLOAT,
                temperature_cell    FLOAT,
                temperature_ambient FLOAT       DEFAULT 25.0,
                charge_rate_kw      FLOAT       DEFAULT 0.0,
                is_charging         BOOLEAN     DEFAULT FALSE,

                -- Extended ML features (required by the anomaly/SoH model)
                internal_resistance   FLOAT     NOT NULL,
                action_voltage        FLOAT     NOT NULL,
                action_current        FLOAT     NOT NULL,
                dT_dt                 FLOAT     NOT NULL,
                dV_dt                 FLOAT     NOT NULL,
                thermal_stress_index  FLOAT     NOT NULL,
                aging_indicator       FLOAT     NOT NULL,
                charging_efficiency   FLOAT     NOT NULL,
                charging_time         FLOAT     NOT NULL,
                cycle_degradation     FLOAT     NOT NULL,
                balancing_time        FLOAT     NOT NULL
            );

            -- Safety net for databases created before these columns existed:
            -- adds them as nullable if the table already exists without them.
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS internal_resistance FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS action_voltage FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS action_current FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS dT_dt FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS dV_dt FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS thermal_stress_index FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS aging_indicator FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS charging_efficiency FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS charging_time FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS cycle_degradation FLOAT;
            ALTER TABLE telemetry_events ADD COLUMN IF NOT EXISTS balancing_time FLOAT;

            -- Fast lookup: "get last 50 readings for vehicle EV-014"
            CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_time
                ON telemetry_events (vehicle_id, recorded_at DESC);

            -- ──────────────────────────────────────────────────────
            -- ML_PREDICTIONS TABLE
            -- Stores the output from your ML model API.
            -- We cache predictions here so we don't call the ML API
            -- on every dashboard refresh (saves time + cost).
            -- ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS ml_predictions (
                id                 UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id         TEXT        NOT NULL REFERENCES vehicles(vehicle_id),
                predicted_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                rul_days           INTEGER,
                soh_forecast_30d   FLOAT,
                soh_forecast_90d   FLOAT,
                degradation_rate   FLOAT,
                confidence_score   FLOAT
            );

            CREATE INDEX IF NOT EXISTS idx_predictions_vehicle_time
                ON ml_predictions (vehicle_id, predicted_at DESC);

            -- ──────────────────────────────────────────────────────
            -- ALERTS TABLE
            -- One row per alert. resolved_at = NULL means still active.
            -- ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS alerts (
                id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id   TEXT        NOT NULL REFERENCES vehicles(vehicle_id),
                severity     TEXT        NOT NULL,   -- 'critical' | 'warning' | 'info'
                alert_type   TEXT        NOT NULL,   -- 'soh_low' | 'thermal' | etc.
                message      TEXT        NOT NULL,
                triggered_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                resolved_at  TIMESTAMPTZ             -- NULL = still active
            );

            CREATE INDEX IF NOT EXISTS idx_alerts_vehicle
                ON alerts (vehicle_id, triggered_at DESC);

            -- ──────────────────────────────────────────────────────
            -- RECOMMENDATIONS TABLE
            -- Charging and maintenance advice per vehicle.
            -- ──────────────────────────────────────────────────────
            CREATE TABLE IF NOT EXISTS recommendations (
                id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
                vehicle_id       TEXT        NOT NULL REFERENCES vehicles(vehicle_id),
                rec_type         TEXT        NOT NULL,
                message          TEXT        NOT NULL,
                charge_limit_pct INTEGER,
                priority         INTEGER     DEFAULT 3,
                created_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );

        """)
    print("✅ Database tables ready")
