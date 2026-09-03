"""
AetherSAR - Canonical detection schema.

Structured person-detection records produced by the CV pipeline.

Geographic coordinates are deliberately ABSENT: victim geolocation is not
implemented yet, so no latitude/longitude is invented for a detection.
A Phase 5 location-association step may add estimated coordinates later.
"""

import math
from datetime import datetime, timezone
from typing import Optional

DETECTION_FIELDS = ("timestamp", "drone_id", "frame_id", "class", "confidence", "bbox")
BBOX_FIELDS = ("x1", "y1", "x2", "y2")
DEFAULT_DRONE_ID = "DRONE-01"


def _now_utc_z() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _require_number(value, name: str, *, minimum: Optional[float] = None, maximum: Optional[float] = None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got boolean {value!r}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    if minimum is not None and result < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {result}")
    if maximum is not None and result > maximum:
        raise ValueError(f"{name} must be <= {maximum}, got {result}")
    return result


def validate_confidence(value) -> float:
    """Validate a detection confidence in [0, 1]; returns it as a float."""
    return _require_number(value, "confidence", minimum=0.0, maximum=1.0)


def build_detection(
    *,
    drone_id: str = DEFAULT_DRONE_ID,
    frame_id: int,
    class_name: str,
    confidence: float,
    bbox: dict,
    timestamp: Optional[str] = None,
) -> dict:
    """Build a canonical detection record (all values validated).

    Example output:
        {
            "timestamp": "2026-09-03T08:15:30.123Z",
            "drone_id": "DRONE-01",
            "frame_id": 42,
            "class": "person",
            "confidence": 0.87,
            "bbox": {"x1": 120, "y1": 80, "x2": 250, "y2": 310},
        }
    """
    if timestamp is None:
        timestamp = _now_utc_z()
    detection = {
        "timestamp": timestamp,
        "drone_id": drone_id,
        "frame_id": frame_id,
        "class": class_name,
        "confidence": confidence,
        "bbox": dict(bbox),
    }
    return validate_detection(detection)


def validate_detection(detection: dict) -> dict:
    """Validate a detection dict; returns it unchanged on success."""
    if not isinstance(detection, dict):
        raise ValueError("detection must be a dict")
    missing = [field for field in DETECTION_FIELDS if field not in detection]
    if missing:
        raise ValueError(f"detection missing required fields: {missing}")

    timestamp = detection["timestamp"]
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise ValueError("timestamp must be a non-empty string")
    drone_id = detection["drone_id"]
    if not isinstance(drone_id, str) or not drone_id.strip():
        raise ValueError("drone_id must be a non-empty string")
    class_name = detection["class"]
    if not isinstance(class_name, str) or not class_name.strip():
        raise ValueError("class must be a non-empty string")

    frame_id = detection["frame_id"]
    if isinstance(frame_id, bool) or not isinstance(frame_id, int):
        raise ValueError(f"frame_id must be an integer, got {frame_id!r}")
    if frame_id < 0:
        raise ValueError(f"frame_id must be >= 0, got {frame_id}")

    validate_confidence(detection["confidence"])

    bbox = detection["bbox"]
    if not isinstance(bbox, dict):
        raise ValueError("bbox must be a dict with x1, y1, x2, y2")
    missing_bbox = [field for field in BBOX_FIELDS if field not in bbox]
    if missing_bbox:
        raise ValueError(f"bbox missing required fields: {missing_bbox}")
    x1 = _require_number(bbox["x1"], "bbox.x1", minimum=0)
    y1 = _require_number(bbox["y1"], "bbox.y1", minimum=0)
    x2 = _require_number(bbox["x2"], "bbox.x2", minimum=0)
    y2 = _require_number(bbox["y2"], "bbox.y2", minimum=0)
    if x2 <= x1:
        raise ValueError(f"bbox x2 ({x2}) must be greater than x1 ({x1})")
    if y2 <= y1:
        raise ValueError(f"bbox y2 ({y2}) must be greater than y1 ({y1})")

    return detection