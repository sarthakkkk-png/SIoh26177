# AetherSAR — Architecture & Design Document

> **Design documentation only.** This document describes the planned Phase 5
> system (FastAPI backend, dashboard, database) and the Phase 1–4 foundations.
> The Python modules in `planner/`, `simulator/`, and `cv/` are the source of
> truth; canonical data schemas live in `docs/SCHEMAS.md`.

## 1. Project Objective

**Problem**  
Search-and-rescue teams face delayed location of missing or injured persons in outdoor environments because manual review of large volumes of aerial imagery is slow, operator cognitive load is high, and systematic area coverage is difficult to maintain under time pressure.

**Solution**  
A software platform that lets an operator define a search mission and area, automatically generates a systematic lawnmower search path, drives a clearly labelled simulated drone that emits telemetry and imagery, runs computer-vision person detection on those images, associates detections with estimated geographic locations, stores all data, raises real-time alerts, and produces a mission report — all visible in a live command-center dashboard.

**One-line definition**  
AetherSAR is a simulation-first, AI-assisted search-and-rescue command platform that closes the loop from mission definition and systematic path planning through simulated flight, computer-vision person detection, estimated geolocation, real-time alerting, and automated reporting.

## 2. Problem Statement

Time-critical location of missing or injured persons in outdoor and post-disaster environments is limited by:
- Slow manual review of large volumes of aerial imagery
- High cognitive load on human operators
- Difficulty maintaining systematic area coverage under time pressure
- Short flight endurance and limited autonomy of current UAV systems
- Lack of integrated detection-to-alert-to-report workflows

## 3. Proposed Solution

AetherSAR provides an integrated software platform that:
- Allows an operator to create a mission and define a search area
- Automatically generates a systematic lawnmower (grid) search path
- Executes the mission using a Python-based drone simulator that emits clearly labelled SIMULATED telemetry
- Supplies aerial imagery to a computer-vision pipeline
- Detects persons using a lightweight YOLO model
- Associates detections with estimated geographic locations using drone pose and a simplified camera model
- Stores missions, telemetry, detections, and alerts
- Raises real-time alerts to the operator
- Displays all information in a live map-centric command-center dashboard
- Generates a mission report on demand

The system is deliberately simulation-first and scoped for a single developer.

## 4. Final MVP

### MUST HAVE
- Mission creation (name, description, priority, search area)
- Search-area definition (rectangle or simple polygon)
- Lawnmower / grid search-path generation producing ordered waypoints
- Python drone simulator emitting labelled SIMULATED telemetry
- Image input (static test images or simple cycling feed from simulator)
- Person detection via lightweight YOLO model producing bounding box + confidence
- Simple estimated location association using drone pose + detection
- Detection event storage and real-time alert
- Live command-center dashboard (map, drone position, path, telemetry, detections, alerts)
- Persistence of missions, telemetry, detections, alerts
- One-click mission report (HTML summary)

### SHOULD HAVE
- Coverage percentage and visited-cell visualization
- Image crop storage for detections
- Basic LLM-generated mission summary and detection explanation (Groq)
- Mission history list
- Simple confidence threshold configuration

### FUTURE
- Real UAV hardware / MAVLink control
- Thermal or multi-sensor fusion
- Adaptive, probabilistic, or reinforcement-learning path planning
- Multi-drone coordination
- Full SLAM, obstacle avoidance, GPS-denied navigation
- Production authentication, BVLOS compliance features, edge deployment on drone

## 5. Complete System Architecture

```
Operator
   ↓
Command Center Dashboard (React)
   ↓
Mission Creation + Search Area
   ↓
FastAPI Backend
   ├── Search Planner → Waypoints
   ├── Mission Manager
   └── WebSocket Hub
   ↓
Drone Simulator (Python)
   ├── Telemetry Engine (SIMULATED)
   └── Camera / Image Source
   ↓
Computer Vision Pipeline (YOLO)
   ↓
Person Detection → Bounding Box + Confidence
   ↓
Location Association (ESTIMATED)
   ↓
Detection Event + Alert Engine
   ↓
Supabase (Postgres + Storage)
   ↓
Dashboard (live update) + Report Generator
   ↓
Groq LLM (explanation / summary layer only)
```

### Detailed ASCII Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        AetherSAR Command Center (Frontend)                  │
│  Landing | Mission Creation | Live Map | Detections | History | Reports     │
└───────────────────────────────┬─────────────────────────────────────────────┘
                                │ REST + WebSocket
┌───────────────────────────────▼─────────────────────────────────────────────┐
│                           FastAPI Backend                                   │
│  Mission Manager │ Search Planner │ Detection Engine │ Alert Engine         │
│  Telemetry Handler │ Report Generator │ WebSocket Hub                       │
└───────┬───────────────────────────┬───────────────────────────┬─────────────┘
        │                           │                           │
        │ Waypoints / Start         │ Telemetry + Images        │ Queries /
        │                           │                           │ Summaries
┌───────▼──────────┐       ┌────────▼────────────┐     ┌────────▼────────────┐
│ Drone Simulator  │       │ Computer Vision     │     │ Groq LLM Layer      │
│ (Python)         │       │ (Ultralytics YOLO)  │     │ (explanations only) │
│ - State          │       │ - Preprocess        │     └─────────────────────┘
│ - Path Follower  │       │ - Detect Person     │
│ - Telemetry      │       │ - BBox + Conf       │
│ - Image Source   │       └─────────┬───────────┘
└───────┬──────────┘                 │ Detection JSON
        │ SIMULATED Telemetry        │
        └────────────────────────────┘
                                │
                    ┌───────────▼───────────┐
                    │      Supabase         │
                    │  Postgres + Storage   │
                    │  missions, telemetry, │
                    │  detections, alerts,  │
                    │  media, reports       │
                    └───────────────────────┘
```

## 6. Component Architecture

| Component | Technology | Purpose | Input | Output | Connects To |
|-----------|------------|---------|-------|--------|-------------|
| Frontend | React + Leaflet/MapLibre + Tailwind | Operator command center | API + WS streams | User actions, mission definitions | FastAPI Backend |
| Mission Manager | FastAPI service | Create, start, stop, status of missions | Mission JSON | Mission records, status events | Supabase, Search Planner, Simulator |
| Search Planner | Pure Python | Generate lawnmower waypoints + coverage grid | Search area polygon/bbox, spacing, altitude | Ordered waypoint list, cell grid | Mission Manager, Simulator |
| Drone Simulator | Python (asyncio) | Simulate flight along waypoints | Waypoints, start/stop | SIMULATED telemetry packets, optional images | Telemetry Engine, Backend |
| Telemetry Engine | Part of Simulator + Backend | Emit and ingest position/status data | Drone state | Timestamped telemetry JSON | Backend, Dashboard |
| Camera/Image Input | Simulator folder or upload | Provide aerial frames | File paths or bytes | Image bytes / URLs | CV Pipeline, Backend |
| Computer Vision | Ultralytics YOLOv8n / YOLO11n | Detect persons in aerial images | Preprocessed image | Boxes, class, confidence | Detection Engine |
| Detection Engine | FastAPI service | Orchestrate CV + create events | Image + drone pose | Detection records | CV, Location Association, Supabase |
| Location Association | Python utility | Estimate lat/lon of detection | Drone pose + bbox center + simple camera model | Estimated lat/lon | Detection Engine |
| FastAPI Backend | FastAPI + Uvicorn | Central API and orchestration | All client & sim requests | JSON, WS messages | All components |
| WebSocket | FastAPI WebSocket | Real-time push of telemetry, detections, alerts | Internal events | Live updates | Frontend |
| Supabase | Postgres + Storage | Persist structured data and media | Rows + files | Query results, public URLs | Backend |
| Alert Engine | FastAPI service | Create and broadcast operator alerts | Detection events | Alert records + WS messages | Supabase, Frontend |
| Groq/LLM | Groq API (Llama-family) | Natural-language summaries and explanations | Mission context, detections | Text summaries | Backend (report & alert wording) |
| Report Generator | FastAPI + simple HTML/PDF | Produce mission summary document | Mission + detections + path | HTML or PDF file | Supabase, Frontend |
| Monitoring | Basic logging + optional health endpoint | Observe service health | Logs, health checks | Console / simple status | Backend |

## 7. Technology Stack

| Layer | Technology | Exact Role | Why |
|-------|------------|------------|-----|
| AI Experimentation | Google Colab | Rapid model testing and light fine-tuning | Free GPU, notebook sharing, quick iteration |
| LLM Inference | Groq | Fast generation of mission summaries and detection explanations | Extremely low latency, simple API, cost-effective for short texts |
| Reasoning / Design Aid | Grok, Google AI Studio | Architecture discussion, prompt refinement | High-quality reasoning; optional |
| Backend Language | Python | Simulator, planner, CV, API | Single language across core logic |
| API Framework | FastAPI | REST + WebSocket server | Fast, typed, excellent async support |
| Computer Vision | Ultralytics YOLO | Person detection | Mature, lightweight nano models, easy deployment |
| Database & Storage | Supabase | Postgres + file storage + optional auth | Managed, generous free tier, simple client |
| Frontend | React + Vite + Tailwind + Leaflet | Command-center UI | Fast to build map-centric dashboards |
| UI Generation | Stitch (Google) | Generate high-fidelity dashboard screens and starter code | Speeds visual design for solo developer |
| Version Control | GitHub | Source, issues, simple CI | Standard |
| Frontend Hosting | Vercel | Deploy React app | Zero-config, free tier, excellent DX |
| Presentation | Canva | Pitch deck and demo slides | Fast professional visuals |
| Optional Screen Aid | Highlight | Contextual help while coding | Convenience only; not part of product |
| Optional Hosting | Hostinger | Not required | Marked optional; Vercel + Supabase suffice |

## 8. Data Flow

1. Operator opens Dashboard and creates a Mission (name, priority, search area drawn on map).
2. Frontend sends `POST /missions` → Backend stores mission in Supabase and returns mission_id.
3. Operator requests path → Backend calls Search Planner → lawnmower waypoints and search cells are generated and stored.
4. Operator starts mission → Backend signals Drone Simulator with waypoints.
5. Simulator advances along waypoints, continuously emitting SIMULATED telemetry (lat, lon, alt, heading, speed, battery, status, timestamp) via WebSocket/HTTP to Backend.
6. Backend stores telemetry samples and broadcasts them over `/ws/missions/{id}` to the Dashboard (map icon and panels update live).
7. At configured intervals or waypoints the Simulator (or test harness) supplies an aerial image.
8. Backend passes image + current drone pose to Computer Vision pipeline.
9. YOLO produces person detections (bounding boxes + confidence).
10. Location Association computes an ESTIMATED latitude/longitude from drone pose + bounding-box center + simple pinhole assumption.
11. Detection Engine creates a Detection record and an Alert; both are written to Supabase.
12. WebSocket pushes the new detection and alert to the Dashboard (pin appears, alert list updates).
13. Operator can open Detection Details (image + box + confidence + estimated coordinates).
14. On mission end or on demand, Report Generator assembles path, detections, coverage and (optionally) calls Groq for a natural-language summary → stores report and returns download link.
15. All persistent state lives in Supabase; the Dashboard remains a pure client.

## 9. Drone/Simulator Architecture

### Drone State (in-memory)
- lat, lon (float)
- altitude_m (float)
- heading_deg (float, 0–360)
- speed_mps (float)
- battery_pct (float)
- status (enum: TAKEOFF, SEARCHING, WAYPOINT_REACHED, LOW_BATTERY, RTH, MISSION_COMPLETE, STOPPED)
- timestamp (ISO 8601 UTC, Z suffix)
- current_waypoint (int, 0-based index of the waypoint being navigated to)
- source = "SIMULATED" (constant)

### Telemetry Packet Format (JSON)

```json
{
  "mission_id": "MISSION-001",
  "timestamp": "2026-09-02T08:15:30.123Z",
  "latitude": 18.520400,
  "longitude": 73.856700,
  "altitude_m": 80.0,
  "heading_deg": 90.0,
  "speed_mps": 8.0,
  "battery_pct": 82.3,
  "status": "SEARCHING",
  "current_waypoint": 3,
  "total_waypoints": 8,
  "source": "SIMULATED"
}
```

The canonical telemetry schema is defined in `docs/SCHEMAS.md` and enforced
by `simulator/telemetry.py` (`validate_telemetry`).

All telemetry is generated by the Python simulator and must be visually and programmatically labelled SIMULATED. No claim is made that this data originates from real flight hardware.

## 10. Search-Area & Path Planning

### Representation
GeoJSON Polygon or simple axis-aligned bounding box + fixed target altitude + lateral track spacing (meters).

### Algorithm (Lawnmower / Boustrophedon)
1. Project geographic bounds to a local metric grid (equirectangular approximation sufficient for small areas).
2. Create parallel tracks spaced by the chosen spacing.
3. Traverse tracks in alternating directions, inserting short connector segments.
4. Convert the resulting points back to latitude/longitude → ordered waypoint list.
5. Simultaneously create a regular cell grid for coverage tracking.

### Coverage
A cell is marked visited when the drone’s ground track comes within a configurable sensor footprint radius of the cell center.  
`coverage_pct = (visited_cells / total_cells) * 100`.

### Drone Movement
Simulator flies sequentially to each waypoint at configured speed, updates state, and emits telemetry. No dynamic re-planning in MVP.

### ASCII Visualization

```
Search Area
┌─────────────────────────────────────┐
│ →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→ │  Track 1
│                                 ↓   │
│ ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←← │  Track 2
│ ↓                                   │
│ →→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→→ │  Track 3
│ ...                                 │
└─────────────────────────────────────┘
```

## 11. Computer Vision Architecture

```
Aerial Image (RGB)
      ↓
Preprocessing (resize ≤ 640 px, letterbox, normalize)
      ↓
Object Detection Model (YOLOv8n or YOLO11n)
      ↓
Person class filter + confidence threshold
      ↓
Bounding Box (xyxy) + Confidence
      ↓
Detection Event
```

- **Recommended model**: Ultralytics YOLOv8n (or current nano equivalent).
- **Input**: RGB image (numpy / PIL / tensor).
- **Output**: List of (bbox, confidence, class_id) for class “person”.
- **Role**: Produce candidate person detections only.
- **Where it runs**: Inside the Backend process or a thin Python worker on the same machine.
- **Connection**: Backend receives image + current drone pose → calls detection function → receives boxes → proceeds to location association.

No accuracy figures are claimed; evaluation is qualitative plus basic precision/recall on a small held-out set of public aerial images.

## 12. Location Association

### Available data
- REAL (from system): detection bounding box, confidence, timestamp, image.
- SIMULATED: drone latitude, longitude, altitude, heading, timestamp.
- Camera intrinsics / mounting angles: assumed or configured constants for MVP.

### Method (MVP – demonstrable estimate)
1. Take the center pixel of the bounding box.
2. Using a simple pinhole camera model and the known (or assumed) camera FOV / focal length, compute the viewing ray in the drone body frame.
3. Transform the ray by the drone’s heading and a level-flight assumption.
4. Intersect the ray with a flat ground plane at the reported altitude.
5. Convert the resulting ground offset into an ESTIMATED latitude and longitude.

### Clear labelling
- The resulting coordinates are always presented as “Estimated location”.
- UI and reports must state that the value is an approximation derived from simulated pose and a simplified camera model.
- Exact GPS from a bounding box alone is never claimed.

## 13. Backend Architecture

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/missions` | POST | Create new mission |
| `/missions` | GET | List missions |
| `/missions/{mission_id}` | GET | Retrieve mission details + status |
| `/missions/{mission_id}/search-path` | POST | Generate and store lawnmower waypoints |
| `/missions/{mission_id}/start` | POST | Start simulator for this mission |
| `/missions/{mission_id}/stop` | POST | Stop / RTH |
| `/telemetry` | POST | Ingest telemetry packet (or use WS) |
| `/missions/{mission_id}/telemetry` | GET | Recent telemetry samples |
| `/detections` | POST | Create detection (internal / test) |
| `/missions/{mission_id}/detections` | GET | List detections |
| `/missions/{mission_id}/alerts` | GET | List alerts |
| `/missions/{mission_id}/report` | GET/POST | Generate or retrieve mission report |
| `/ws/missions/{mission_id}` | WebSocket | Live telemetry, detections, alerts, status |

All write endpoints perform basic validation and write to Supabase. WebSocket is the primary real-time channel to the dashboard.

## 14. Supabase Database Architecture

### missions
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | Unique mission identifier |
| name | text | | Human name |
| description | text | | Optional notes |
| priority | text | | low / medium / high |
| status | text | | created / planned / flying / completed / failed |
| search_area | jsonb | | GeoJSON or bbox |
| created_at | timestamptz | | |
| updated_at | timestamptz | | |

### telemetry
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | bigserial | PK | |
| mission_id | uuid | FK → missions | |
| timestamp | timestamptz | | |
| lat, lon, altitude_m, heading_deg, speed_mps, battery_pct | float | | |
| status | text | | |
| source | text | | Always “SIMULATED” for MVP |
| raw | jsonb | | Optional full packet |

### search_cells
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | |
| mission_id | uuid | FK | |
| cell_index | int | | |
| center_lat, center_lon | float | | |
| visited | boolean | | |
| visited_at | timestamptz | | |

### detections
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | |
| mission_id | uuid | FK | |
| timestamp | timestamptz | | |
| confidence | float | | |
| bbox | jsonb | | [x1,y1,x2,y2] |
| estimated_lat, estimated_lon | float | | ESTIMATED |
| image_url | text | | Supabase Storage URL |
| notes | text | | |

### alerts
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | |
| mission_id | uuid | FK | |
| detection_id | uuid | FK | |
| severity | text | | |
| message | text | | |
| created_at | timestamptz | | |
| acknowledged | boolean | | |

### media
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | |
| mission_id | uuid | FK | |
| detection_id | uuid | FK (nullable) | |
| url | text | | |
| type | text | | image / crop |

### reports
| Column | Type | Key | Purpose |
|--------|------|-----|---------|
| id | uuid | PK | |
| mission_id | uuid | FK | |
| content_html | text | | |
| file_url | text | | |
| generated_at | timestamptz | | |

### mission_events (optional lightweight audit)
id, mission_id, event_type, payload (jsonb), created_at.

Relationships are simple foreign keys from child tables to missions (and detections where relevant).

## 15. Groq/LLM Architecture

Groq sits strictly as an **intelligence / explanation layer** after detection and storage:

- Generate concise mission summary text for reports.
- Produce human-readable detection explanations.
- Draft alert message wording.
- Answer simple natural-language queries about a completed mission.

**Explicit non-responsibilities**  
Groq does **not** generate motor commands, set waypoints, perform flight stabilization, decide obstacle avoidance, or exercise any safety-critical control. All flight logic remains deterministic Python inside the Simulator and Search Planner.

## 16. Frontend Architecture

### Landing
- Project title, one-line description, “Simulation Prototype” badge, Launch Command Center CTA.
- No API calls required beyond static content.

### Mission Creation
- Form (name, description, priority).
- Interactive map for drawing rectangle/polygon.
- Actions: Save Mission → `POST /missions`; Generate Path → `POST .../search-path`.

### Live Mission
- Central map: search area, planned path, live drone icon, detection pins, optional coverage overlay.
- Side panel: telemetry (lat/lon/alt/heading/speed/battery/status), coverage %, active alerts.
- Event feed.
- Data via `GET /missions/{id}` + WebSocket `/ws/missions/{id}`.
- Actions: Start / Stop.

### Detection Details
- Modal or panel: image with bounding-box overlay, confidence, estimated coordinates, timestamp, acknowledge button.
- Data from detection record.

### Mission History
- Table/list of past missions with status, detection count, link to report.
- `GET /missions`.

### Reports
- Rendered HTML or downloadable file produced by `GET/POST .../report`.

## 17. GitHub Repository Structure

> The Phase 5 components below (`backend/`, `ai/`, `frontend/`, `database/`)
> are planned. The implemented Phase 1–4 layout (`planner/`, `simulator/`,
> `cv/`, `tests/`, `docs/`) is documented in the repository README.

```
AetherSAR/
├── README.md                 # Overview, quick start, demo instructions
├── docs/
│   ├── FINAL_ARCHITECTURE.md # This document
│   ├── api.md
│   └── demo-script.md
├── simulator/
│   ├── main.py
│   ├── drone.py
│   ├── path_follower.py
│   └── telemetry.py
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── api/              # routers
│   │   ├── services/         # planner, detection, alert, report
│   │   ├── models/
│   │   └── ws.py
│   ├── requirements.txt
│   └── .env.example
├── ai/
│   ├── detect.py
│   ├── geolocate.py
│   └── weights/              # .pt files (LFS or ignored)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   └── lib/
│   ├── package.json
│   └── ...
├── database/
│   └── schema.sql
├── notebooks/                # Colab exports for CV experiments
├── tests/
└── scripts/                  # seed data, path-planner CLI, etc.
```

## 18. Real vs Simulated vs Estimated vs Future

| Feature | Status | Explanation |
|---------|--------|-------------|
| Mission creation & search area definition | 🟢 REAL SOFTWARE | Fully implemented UI + backend + DB |
| Lawnmower search-path generation | 🟢 REAL SOFTWARE | Deterministic Python algorithm |
| Drone motion & telemetry stream | 🟡 SIMULATED | Python simulator; every packet labelled SIMULATED |
| Aerial imagery source | 🟡 SIMULATED | Test images or simple feed; not live camera from real UAV |
| Person detection (YOLO) | 🟢 REAL SOFTWARE | Actual model inference |
| Geographic location of detection | 🟠 ESTIMATED | Computed from simulated pose + simplified camera model |
| Alerts, storage, dashboard updates | 🟢 REAL SOFTWARE | Real-time via WebSocket + Supabase |
| Mission report generation | 🟢 REAL SOFTWARE | Assembled from stored data (+ optional LLM text) |
| LLM summaries / explanations | 🟢 REAL SOFTWARE | Groq calls for text only |
| Real UAV hardware control | 🔵 FUTURE | Out of scope |
| Thermal / multi-modal sensing | 🔵 FUTURE | Out of scope |
| Adaptive or multi-drone planning | 🔵 FUTURE | Out of scope |
| Regulatory BVLOS autonomy | 🔵 FUTURE | Out of scope |

## 19. Security & Reliability

- **API authentication**: Optional simple API key or Supabase JWT for demo; open endpoints acceptable for local/hackathon demo with clear warning.
- **Database access**: Supabase service role key kept server-side only; anon key restricted.
- **Input validation**: Pydantic models on all FastAPI endpoints; reject malformed coordinates, empty areas, out-of-range altitudes.
- **Model failures**: CV exceptions caught; detection simply omitted; system continues.
- **False detections**: Confidence threshold + operator review; alerts are advisory only.
- **Communication loss**: Simulator continues; Backend marks mission degraded; Dashboard shows last-known state.
- **Missing telemetry**: Dashboard displays “stale” indicator after timeout.
- **Invalid coordinates**: Planner and geolocation guard against NaN / out-of-bounds values.

## 20. Solo-Developer Development Order

1. **Architecture finalization**  
   INPUT: this document → ACTION: review & freeze → OUTPUT: `docs/FINAL_ARCHITECTURE.md` → DONE: document committed.

2. **GitHub repository**  
   INPUT: structure above → ACTION: create repo, folders, README → OUTPUT: empty but organized repo → DONE: clone works.

3. **Google Colab AI experiment**  
   INPUT: public aerial images → ACTION: run YOLO inference, draw boxes → OUTPUT: working `detect.py` prototype + sample results → DONE: can detect persons on test images.

4. **Search Planner**  
   INPUT: bbox + spacing → ACTION: implement lawnmower + cell grid → OUTPUT: pure functions returning waypoints & cells → DONE: unit-testable path generation.

5. **Drone Simulator**  
   INPUT: waypoints → ACTION: asyncio state machine + telemetry emission → OUTPUT: running simulator process → DONE: telemetry stream visible and labelled SIMULATED.

6. **Supabase schema**  
   INPUT: schema.sql → ACTION: create project & tables → OUTPUT: live database → DONE: can insert/query via client.

7. **FastAPI Backend core**  
   INPUT: endpoint list → ACTION: implement routers, services, WS → OUTPUT: running API → DONE: create mission, start sim, receive telemetry.

8. **CV + Location Association integration**  
   INPUT: image + pose → ACTION: wire detection → geolocation → detection record → OUTPUT: end-to-end detection events → DONE: detection appears in DB and via WS.

9. **Frontend**  
   INPUT: Stitch designs + API → ACTION: build pages, map, live updates → OUTPUT: working dashboard → DONE: full create → fly → detect loop visible in browser.

10. **Alerts, Reports, optional Groq**  
    INPUT: detection events → ACTION: alert engine + report generator → OUTPUT: alerts + downloadable report → DONE: one-click report works.

11. **Integration testing & polish**  
    INPUT: full system → ACTION: run demo script repeatedly → OUTPUT: reliable 3–5 min flow → DONE: demo is stable.

12. **Deployment & presentation**  
    INPUT: working code → ACTION: Vercel frontend, public README, Canva slides → OUTPUT: live URL + pitch deck → DONE: ready for judges.

## 21. Final Hackathon Demo Flow

1. Open Dashboard (Landing → Launch Command Center).
2. Create Mission → enter name/priority → draw search rectangle.
3. Generate Search Path → waypoints and path appear on map.
4. Start Simulation → clearly announce “All flight data is SIMULATED”.
5. Drone icon moves along path; telemetry panel updates live (battery decreases, status = FLYING).
6. When a test image is processed → YOLO runs → bounding box drawn.
7. Detection Event created → estimated location calculated → map pin appears.
8. Alert appears in the alert list / toast.
9. Click detection → detail view shows image, box, confidence, estimated coordinates.
10. Stop mission → Generate Report → show summary containing path, detections, and coverage.
11. Briefly show Mission History to prove persistence in Supabase.

Language remains precise: simulated drone, estimated location, prototype command center.

## 22. Final Architecture Summary

**Project Name**  
AetherSAR

**Problem**  
Time-critical location of missing persons is slowed by manual imagery review and lack of systematic aerial coverage.

**Solution**  
Simulation-first platform that plans a lawnmower search, flies a labelled simulated drone, detects persons with computer vision, estimates their locations, raises alerts, and produces reports inside a live command-center dashboard.

**MVP**  
Mission create → search area → lawnmower path → simulated flight + telemetry → YOLO person detection → estimated geolocation → real-time alert → dashboard update → mission report.

**Architecture**  
Dashboard ↔ FastAPI (Mission Manager, Search Planner, Detection Engine, Alert Engine, WebSocket) ↔ Python Drone Simulator (SIMULATED telemetry + images) ↔ YOLO CV ↔ Location Association (ESTIMATED) ↔ Supabase ↔ Groq (explanation layer only).

**Tech Stack**  
Python, FastAPI, Ultralytics YOLO, Supabase, React + Leaflet, Groq, Vercel, Google Colab, Stitch, GitHub, Canva.

**AI Pipeline**  
Aerial image → preprocess → YOLOv8n/YOLO11n → person boxes + confidence → estimated lat/lon from simulated pose → detection event.

**Data Flow**  
Operator → Dashboard → Backend → Planner → Simulator → Telemetry + Image → CV → Detection + Estimated Location → Supabase + WS → Dashboard Alert → optional Groq summary → Report.

**Database**  
missions, telemetry, search_cells, detections, alerts, media, reports (simple FK relationships to missions).

**API**  
REST endpoints for missions, path, start/stop, telemetry, detections, alerts, report + WebSocket `/ws/missions/{id}` for live updates.

**Repository Structure**  
AetherSAR/ with frontend/, backend/, ai/, simulator/, database/, notebooks/, tests/, docs/, README.md.

**Real / Simulated / Future**  
🟢 Real software: mission logic, path planning, CV, storage, dashboard, reports.  
🟡 Simulated: drone flight and telemetry.  
🟠 Estimated: detection geographic coordinates.  
🔵 Future: real hardware, thermal, adaptive/multi-drone planning, regulatory autonomy.

**Demo Flow**  
Create mission → define area → generate path → start simulated flight → live telemetry → AI detection → estimated location + alert → stored data → mission report.

## 23. Future Scope

- Real UAV hardware bridge and MAVLink integration
- Thermal / multi-spectral sensor fusion
- Adaptive and probabilistic search planning
- Multi-UAV coordination
- Full SLAM and GPS-denied navigation
- Edge deployment on drone companion computers
- Field trials under proper regulatory authorization (Part 107 / public aircraft / SORA)
- Integration with existing SAR incident management systems

---

**Document Status**  
Architecture Version: 1.0  
Project Type: Hackathon Prototype  
Development Model: Solo Developer  
Primary Goal: Working AI-assisted search-and-rescue demonstration
