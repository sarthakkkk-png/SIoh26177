"""
AetherSAR - Waypoint loading and validation.

Canonical waypoint structure (shared by legacy waypoint files and the
generated search path):

    {"latitude": float, "longitude": float}

All coordinates are validated as finite WGS84 values; invalid waypoints are
rejected with ValueError instead of being silently converted.
"""

import json
from pathlib import Path
from typing import List

from planner.coordinates import validate_lat_lon

WAYPOINT_FIELDS = ("latitude", "longitude")


def validate_waypoint(waypoint) -> dict:
    """Validate a single waypoint; returns a normalized {latitude, longitude} dict."""
    if not isinstance(waypoint, dict):
        raise ValueError(f"waypoint must be a dict, got {type(waypoint).__name__}")
    missing = [field for field in WAYPOINT_FIELDS if field not in waypoint]
    if missing:
        raise ValueError(f"waypoint missing required fields: {missing}")
    latitude, longitude = validate_lat_lon(waypoint["latitude"], waypoint["longitude"])
    return {"latitude": latitude, "longitude": longitude}


def load_waypoints(path) -> List[dict]:
    """Load and validate a waypoint file (JSON list of waypoint dicts)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Waypoint file not found: {path}")
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValueError("Waypoint file must contain a list of waypoints")
    if len(data) == 0:
        raise ValueError("Waypoint file must contain at least one waypoint")
    return [validate_waypoint(waypoint) for waypoint in data]