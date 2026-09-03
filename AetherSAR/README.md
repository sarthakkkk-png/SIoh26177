# AetherSAR

**A simulated autonomous search-and-rescue drone prototype.**

AetherSAR demonstrates an end-to-end search-and-rescue workflow in
simulation: define a search area, generate a systematic lawnmower search
path, fly a clearly labelled simulated drone that emits telemetry, run
computer-vision person detection on frames, and (in Phase 5) surface
everything in a live command-center dashboard.

**All flight data is SIMULATED.** Nothing in this repository controls a
physical UAV.

## Current capabilities

- Waypoint-based drone simulation (position, heading, speed, battery, status)
- Telemetry generation and JSONL persistence (every record tagged
  `"source": "SIMULATED"`)
- Geographic distance and bearing calculations (Haversine; equirectangular
  approximation for small areas)
- Search-area abstraction (validated WGS84 bounding box)
- Automated lawnmower (boustrophedon) search-path generation
- Simulated return-to-home behavior at critical battery
- Structured person-detection schema and a clean detector interface
  (optional pretrained-model adapter; see "Computer vision" below)
- FastAPI backend: missions, search paths, telemetry and detection ingestion,
  and a WebSocket event stream (see "Phase 5 backend" below)
- Canonical data schemas documented in `docs/SCHEMAS.md`

## Architecture

```
Search Area
    ↓
Search Planner (lawnmower waypoint generation)
    ↓
Drone Simulator (state, movement, battery)
    ↓
Telemetry (canonical JSONL records, source=SIMULATED)
    ↓
CV Detection (interface + optional pretrained-model adapter)
    ↓
Detection Events (canonical schema, no invented coordinates)
    ↓
Phase 5 Backend (FastAPI - missions, search paths, telemetry, detections, WebSocket)
    ↓
Future Dashboard
```

## Repository layout

```
AetherSAR/
├── simulator/          # drone state, movement, telemetry, mission engine, CLI
│   ├── main.py         # mission runner (generated or manual waypoints)
│   ├── drone.py
│   ├── path_follower.py
│   ├── telemetry.py    # canonical telemetry schema + JSONL persistence
│   ├── mission.py      # mission engine incl. simulated RTH at critical battery
│   ├── waypoints.py    # waypoint loading and validation
│   ├── waypoints.json  # legacy manual waypoint set
│   └── tests/
├── planner/            # search-area abstraction + lawnmower path generation
│   ├── search_area.py
│   ├── search_planner.py
│   └── coordinates.py  # WGS84 coordinate validation
├── cv/                 # canonical detection schema + detector interface
│   ├── detection.py
│   └── detect.py
├── backend/            # Phase 5 FastAPI backend (in-memory storage, no DB)
│   ├── main.py
│   ├── schemas.py      # Pydantic models mirroring the canonical schemas
│   ├── store.py        # in-memory store
│   ├── websocket.py    # WebSocket connection manager
│   ├── routes/
│   └── tests/
├── tests/              # top-level test suites + run_all runner
├── docs/
│   ├── AetherSAR_Architecture.md   # Phase 5 design document
│   └── SCHEMAS.md                  # canonical data schemas
└── README.md
```

## Quick start

From the repository root (`AetherSAR/`), Python 3.10+, no dependencies:

```bash
# Generated lawnmower mission over the default search area (real-time pacing)
python3 -m simulator.main

# Custom search area and track spacing
python3 -m simulator.main --area 18.5204 73.8567 18.5228 73.8599 --spacing 85

# Legacy manual waypoint file
python3 -m simulator.main --waypoints simulator/waypoints.json

# Run instantly without wall-clock pacing (fast verification)
python3 -m simulator.main --no-delay

# Run every test suite
python3 -m tests.run_all

# Run a single test suite
python3 -m simulator.tests.test_simulator
python3 -m tests.test_search_planner
```

The legacy invocation from inside the simulator directory also still works:

```bash
cd simulator
python3 main.py
```

Telemetry is written to `simulator/output/telemetry.jsonl` (one JSON object
per line).

## Phase 5 backend

The backend is a local FastAPI integration layer over the Phase 1-4 modules:
it stores missions and their generated search paths, ingests telemetry and
person-detection events (validated against the canonical schemas), and
broadcasts live events over WebSocket for a future dashboard.

Storage is **in-memory only** (no database) and resets on restart.

```bash
# Install backend dependencies
pip install -r backend/requirements.txt

# Start the server (from the AetherSAR/ directory)
python3 -m uvicorn backend.main:app --reload
```

Interactive API docs: http://127.0.0.1:8000/docs

Main endpoints:

| Method | Path | Purpose |
|---|---|---|
| POST | `/missions` | Create a mission with a search area |
| GET | `/missions/{id}` | Mission details |
| POST | `/missions/{id}/search-path` | Generate lawnmower waypoints (existing planner) |
| GET | `/missions/{id}/search-path` | Stored search path |
| POST | `/telemetry` | Ingest a canonical telemetry record |
| GET | `/missions/{id}/telemetry` | Stored telemetry for a mission |
| POST | `/detections` | Ingest a canonical detection record (wrapped with mission_id) |
| GET | `/missions/{id}/detections` | Stored detections for a mission |
| WS | `/ws/missions/{id}` | Live mission events (telemetry, detections, search path) |
| GET | `/health` | Health check |

Backend limitations:

- In-memory storage: data is lost on restart (no database yet).
- Telemetry and detection ingestion require the mission to exist first
  (`POST /missions`) - orphan records are rejected with 404.
- Detections carry **no geographic coordinates** (geolocation is not
  implemented; coordinates are never invented).
- CV runtime inference remains unverified; the detection API accepts any
  record conforming to the canonical schema.
- No dashboard/frontend yet - the WebSocket stream is the future UI channel.

## Computer vision

`cv/detect.py` defines the detector interface (`BaseDetector`) and
`UltralyticsPersonDetector`, an adapter for a pretrained Ultralytics YOLO
model (COCO "person" class). Runtime inference is **optional**: it requires
the `ultralytics` package and, on first use, network access to download the
model weights (yolov8n.pt, AGPL-3.0 via the Ultralytics project).

```bash
pip install -r requirements-cv.txt

# Run real person detection on an image (canonical records printed)
python3 -m cv.detect cv/samples/bus.jpg

# Machine-readable output
python3 -m cv.detect cv/samples/bus.jpg --json
```

`cv/samples/bus.jpg` is the public Ultralytics YOLO demo image (source and
license documented in `cv/samples/README.md`), used to verify inference
end-to-end.

### VERIFIED

- Detector adapter loads a real model and runs inference
  (`UltralyticsPersonDetector`, YOLOv8n on CPU).
- Real model outputs convert into the canonical 6-field detection schema
  (`class`, `confidence`, `bbox`, `frame_id`, `timestamp`, `drone_id`) and
  pass the existing `cv.detection.validate_detection`.
- Real detections are ingested by the Phase 5 backend
  (`POST /detections` with the `{mission_id, detection}` wrapper) and
  retrieved via `GET /missions/{id}/detections`.
- The canonical detection schema carries no geographic coordinates.

### NOT VERIFIED

- No detection accuracy/precision/recall/mAP/FPS figures exist - there is no
ground-truth evaluation in this repository.
- The bundled sample image is a ground-level street scene, not aerial
  imagery; no aerial or search-and-rescue detection performance is claimed.
- Detection-to-GPS geolocation is not implemented.

### Runtime tests

`tests/test_cv_runtime.py` runs real inference when the optional stack is
installed and skips gracefully otherwise, so the automated suite never
depends on internet access or model downloads.

## Explicit limitations

- **Simulation only** - all flight data is generated by software and labelled
  `SIMULATED`; nothing controls a real aircraft.
- **Not flight-ready** - there is no flight controller, no real failsafe, no
  obstacle avoidance, no SLAM, and no GPS-denied navigation.
- **No multi-drone coordination.**
- **No guaranteed detection accuracy** - detections depend on the pretrained
  model and input imagery; none has been measured in this repository.
- **No automatic victim GPS geolocation** - detections deliberately carry no
  geographic coordinates until a location-association step is implemented.
- **No production safety guarantees** - the simulated return-to-home behavior
  at critical battery is a demo behavior, not a certified UAV failsafe.