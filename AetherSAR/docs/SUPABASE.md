# AetherSAR — Supabase / PostgreSQL Persistence (Phase 6)

**Supabase provides persistent mission/backend data storage. Detection
geolocation is not implemented yet.**

The backend (FastAPI) remains the single application/API layer. Supabase is
a persistence backend reached only through `backend/database/` — the
dashboard (future) will never talk to the database directly.

```
Drone Simulator
      │
      ▼
   FastAPI  ────► WebSocket ────► Dashboard (future)
      │
      ▼
Persistence facade (backend/store.py)
      │
      ├── SupabasePersistence   (SUPABASE_URL + SUPABASE_KEY set)
      └── InMemoryPersistence   (offline fallback)
```

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `SUPABASE_URL` | only for Supabase mode | Project URL, must be an `http(s)://` URL |
| `SUPABASE_KEY` | only for Supabase mode | Key used backend-side only (service role for the MVP) |

Copy `backend/example.env` to a local `.env` (never committed — `.env` is
gitignored) and run:

```bash
python3 -m uvicorn backend.main:app --reload --env-file .env
```

Or export the variables in your shell. Without valid values the backend
starts normally and uses the in-memory store.

## Local fallback behavior

When `SUPABASE_URL` / `SUPABASE_KEY` are missing, empty, or the URL is not an
http(s) URL:

- the backend starts normally,
- `GET /` reports `"persistence": "memory"`,
- all endpoints behave exactly as before, using the in-memory store,
- data is lost on restart.

With valid credentials, `GET /` reports `"persistence": "supabase"` and all
writes/reads go through Supabase/PostgreSQL. Persistence failures raise a
clear 500 (`persistence error: ...`) — writes are never silently dropped.

## How to create the schema

1. Open the Supabase dashboard → SQL editor.
2. Paste the entire contents of `backend/database/schema.sql` and run it.
3. Copy the project URL and a key into the backend environment.

## Tables

| Table | Purpose | Key relationships |
|---|---|---|
| `missions` | Mission records with `search_area` (JSONB bounding box) | — |
| `drones` | Simulated drones, registered automatically from telemetry `drone_id` | — |
| `telemetry` | Canonical simulator telemetry (one row per record) | `mission_id` → missions, `drone_id` → drones |
| `search_paths` | Generated lawnmower waypoint list per mission | `mission_id` → missions |
| `search_cells` | Grid cells derived from the generated path (`status='pending'`) | `mission_id` → missions |
| `detections` | Canonical detection records; association stored at row level | `mission_id` → missions |
| `alerts` | Operator alerts (structure only — no alert engine yet) | `mission_id`, optional `detection_id` |
| `mission_events` | Audit trail (MISSION_CREATED, SEARCH_PATH_GENERATED, DETECTION_RECEIVED, ...) | `mission_id` → missions |
| `media` | Media metadata (structure only) | `mission_id`, optional `detection_id` |
| `reports` | Report metadata (structure only — generation is later) | `mission_id` → missions |

Canonical field names from `simulator/telemetry.py` and `cv/detection.py`
are used as column names — there is no second telemetry/detection schema.
IDs are `text` so application-generated ids (`uuid4().hex`) round-trip
exactly; serial tables use Postgres `bigint identity`.

## What is persisted

- missions (create → row; telemetry/detection ingestion requires the
  mission row to exist, same 404 semantics as before),
- generated search paths and derived search cells,
- telemetry records (canonical 13 fields, `source='SIMULATED'` enforced),
- detection records (canonical 6 fields — **no latitude/longitude**),
- drones (auto-upserted on first telemetry per drone),
- mission events, and the data structures for alerts, media and reports.

## Security assumptions

- The Supabase key is used backend-side only and never returned to clients.
- Row Level Security is intentionally not enabled for the MVP: the backend
  is the only data consumer. Revisit RLS before any client-side access.

## What is still not implemented

- Detection-to-GPS geolocation (detections carry no coordinates).
- Coverage tracking (search cells stay `pending`; marking cells searched
  needs a coverage engine fed by telemetry `current_waypoint`).
- Alert engine, media upload, and report generation (structures only).
- Real drone hardware and flight control.
