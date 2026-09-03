"""
AetherSAR Phase 5 - API request/response models (Pydantic).

These models mirror the canonical Phase 1-4 schemas documented in
docs/SCHEMAS.md. Authoritative semantic validation lives in the Phase 1-4
modules and is invoked by the API routes:

  - telemetry:      simulator.telemetry.validate_telemetry
  - detection:      cv.detection.validate_detection
  - search area:    planner.search_area.SearchArea

Pydantic here handles JSON typing; the Phase 1-4 validators enforce ranges,
finite values, and canonical field semantics.
"""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class SearchAreaIn(BaseModel):
    """WGS84 bounding box in the canonical SearchArea shape."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float


class MissionCreate(BaseModel):
    name: str = Field(default="", max_length=200)
    search_area: SearchAreaIn


class Mission(BaseModel):
    mission_id: str
    name: str
    status: str
    search_area: dict
    created_at: str


class SearchPathRequest(BaseModel):
    spacing_m: float = 85.0


class SearchPath(BaseModel):
    mission_id: str
    spacing_m: float
    waypoints: List[dict]
    generated_at: str


class TelemetryRecord(BaseModel):
    """Canonical 13-field telemetry record (simulator.telemetry)."""

    drone_id: str
    mission_id: str
    timestamp: str
    latitude: float
    longitude: float
    altitude_m: float
    heading_deg: float
    speed_mps: float
    battery_pct: float
    status: str
    current_waypoint: int
    total_waypoints: int
    source: str


class BBox(BaseModel):
    x1: float
    y1: float
    x2: float
    y2: float


class DetectionRecord(BaseModel):
    """Canonical 6-field detection record (cv.detection).

    Deliberately has no geographic coordinates: victim geolocation is not
    implemented, so latitude/longitude are never invented for a detection.
    """

    model_config = ConfigDict(populate_by_name=True)

    timestamp: str
    drone_id: str
    frame_id: int
    class_name: str = Field(alias="class")
    confidence: float
    bbox: BBox


class DetectionIn(BaseModel):
    """Wraps a canonical detection record with an explicit mission_id.

    The canonical detection record has no mission_id of its own, so mission
    association is made explicit in the request wrapper without modifying
    the canonical record.
    """

    mission_id: str
    detection: DetectionRecord