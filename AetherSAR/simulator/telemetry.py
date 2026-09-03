"""
AetherSAR - Telemetry generation and persistence.

Canonical telemetry fields (see docs/SCHEMAS.md):

    drone_id, mission_id, timestamp, latitude, longitude, altitude_m,
    heading_deg, speed_mps, battery_pct, status, current_waypoint,
    total_waypoints, source

`source` is always "SIMULATED" - this prototype never claims real flight data.
"""

import json
import math
from pathlib import Path
from typing import Dict

from simulator.drone import DroneState

OUTPUT_DIR = Path(__file__).parent / "output"
TELEMETRY_FILE = OUTPUT_DIR / "telemetry.jsonl"

TELEMETRY_FIELDS = (
    "drone_id",
    "mission_id",
    "timestamp",
    "latitude",
    "longitude",
    "altitude_m",
    "heading_deg",
    "speed_mps",
    "battery_pct",
    "status",
    "current_waypoint",
    "total_waypoints",
    "source",
)


def validate_telemetry(telem: Dict) -> Dict:
    """Validate a telemetry record; raises ValueError on problems."""
    if not isinstance(telem, dict):
        raise ValueError("telemetry must be a dict")
    missing = [field for field in TELEMETRY_FIELDS if field not in telem]
    if missing:
        raise ValueError(f"telemetry missing required fields: {missing}")

    latitude = float(telem["latitude"])
    longitude = float(telem["longitude"])
    if not math.isfinite(latitude) or not (-90.0 <= latitude <= 90.0):
        raise ValueError(f"invalid latitude in telemetry: {telem['latitude']!r}")
    if not math.isfinite(longitude) or not (-180.0 <= longitude <= 180.0):
        raise ValueError(f"invalid longitude in telemetry: {telem['longitude']!r}")

    battery_pct = float(telem["battery_pct"])
    if not math.isfinite(battery_pct) or not (0.0 <= battery_pct <= 100.0):
        raise ValueError(f"invalid battery_pct in telemetry: {telem['battery_pct']!r}")

    for field in ("altitude_m", "heading_deg", "speed_mps"):
        value = float(telem[field])
        if not math.isfinite(value):
            raise ValueError(f"non-finite {field} in telemetry: {telem[field]!r}")

    for field in ("current_waypoint", "total_waypoints"):
        if not isinstance(telem[field], int) or telem[field] < 0:
            raise ValueError(f"invalid {field} in telemetry: {telem[field]!r}")

    if telem["source"] != "SIMULATED":
        raise ValueError(f"telemetry source must be SIMULATED, got {telem['source']!r}")

    return telem


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_telemetry(drone: DroneState) -> Dict:
    drone.update_timestamp()
    return validate_telemetry(drone.to_dict())


def print_telemetry(telem: Dict) -> None:
    print(
        f"[SIM] Drone {telem['drone_id']} | "
        f"Pos: {telem['latitude']:.5f}, {telem['longitude']:.5f} | "
        f"Alt: {telem['altitude_m']} m | "
        f"Hdg: {telem['heading_deg']:.0f}° | "
        f"Spd: {telem['speed_mps']} m/s | "
        f"Bat: {telem['battery_pct']:.1f}% | "
        f"WP: {telem['current_waypoint']}/{telem['total_waypoints']} | "
        f"Status: {telem['status']}"
    )


def save_telemetry(telem: Dict, filepath: Path = TELEMETRY_FILE) -> None:
    ensure_output_dir()
    with open(filepath, "a", encoding="utf-8") as file:
        file.write(json.dumps(telem) + "\n")


def clear_telemetry_file(filepath: Path = TELEMETRY_FILE) -> None:
    ensure_output_dir()
    if filepath.exists():
        filepath.unlink()