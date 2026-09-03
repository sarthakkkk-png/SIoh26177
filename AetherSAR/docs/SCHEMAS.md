# AetherSAR - Canonical Data Schemas

This file is the single source of truth for the data structures shared across
the repository. Implementations enforce these schemas (see the referenced
modules); `docs/AetherSAR_Architecture.md` describes the overall system
design.

## Waypoint

Used by: legacy waypoint files, the lawnmower planner, the mission engine.
Enforced by: `simulator/waypoints.py` and `planner/coordinates.py`.

```json
{"latitude": 18.5204, "longitude": 73.8567}
```

- `latitude`: float, finite, in [-90, 90].
- `longitude`: float, finite, in [-180, 180].
- Unknown keys are ignored on load; coordinates are normalized to floats.
- NaN, infinity, missing keys, and out-of-range values are rejected with
  ValueError (never silently converted).

## SearchArea

Used by: `planner/search_area.py` and `planner/search_planner.py`.

```json
{"min_lat": 18.5204, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599}
```

- All four values are finite WGS84 coordinates and `min_lat < max_lat`,
  `min_lon < max_lon`.
- Metric sizes use an equirectangular approximation (1 degree of latitude =
  111,320 m; degrees of longitude scaled by cos(latitude)), suitable for the
  small areas used by this simulated prototype - not production GIS.

## Telemetry

Produced by: `simulator/telemetry.py` (one JSON object per line in
`simulator/output/telemetry.jsonl`). Enforced by `validate_telemetry()`.

```json
{
  "drone_id": "DRONE-01",
  "mission_id": "MISSION-001",
  "timestamp": "2026-09-03T16:53:43.235Z",
  "latitude": 18.5204,
  "longitude": 73.8567,
  "altitude_m": 80.0,
  "heading_deg": 0.0,
  "speed_mps": 8.0,
  "battery_pct": 100.0,
  "status": "TAKEOFF",
  "current_waypoint": 0,
  "total_waypoints": 25,
  "source": "SIMULATED"
}
```

- `timestamp`: ISO-8601 UTC with `Z` suffix.
- `current_waypoint`: 0-based index of the waypoint currently being navigated
  to; it equals the last reached index at the moment of arrival.
- `source`: always `"SIMULATED"` - this prototype never claims real flight
  data.
- Status values with deterministic transitions (see `simulator/mission.py`):
  `TAKEOFF`, `SEARCHING`, `WAYPOINT_REACHED` (transient, emitted on arrival),
  `LOW_BATTERY`, `RTH`, `MISSION_COMPLETE`, `STOPPED`.

## Detection

Produced by: `cv/detect.py` (detector adapters). Enforced by
`cv/detection.py`. No model weights are required to validate this schema.

```json
{
  "timestamp": "2026-09-03T16:53:43.235Z",
  "drone_id": "DRONE-01",
  "frame_id": 42,
  "class": "person",
  "confidence": 0.87,
  "bbox": {"x1": 120, "y1": 80, "x2": 250, "y2": 310}
}
```

- `frame_id`: non-negative integer.
- `confidence`: float in [0, 1].
- `bbox`: pixel box with `x2 > x1`, `y2 > y1`, all values >= 0.
- **No geographic coordinates.** Victim geolocation is not implemented, so
  latitude/longitude must NOT be invented for a detection. A Phase 5
  location-association step may add estimated coordinates explicitly.