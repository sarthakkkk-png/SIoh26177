"""
AetherSAR Phase 5 - detection ingestion.

The canonical detection record (cv/detection.py) has no mission_id, so the
API wraps it as {mission_id, detection} to make mission association explicit
without modifying the canonical record. The stored record remains the exact
canonical 6-field shape.

No geographic coordinates are added: victim geolocation is NOT implemented,
so latitude/longitude are never invented for a detection.
"""

from fastapi import APIRouter, HTTPException

from backend.eventlog import record_event
from backend.schemas import DetectionIn
from backend.store import store
from backend.websocket import manager
from cv.detection import validate_detection

router = APIRouter(tags=["detections"])


@router.post("/detections", status_code=201)
async def ingest_detection(payload: DetectionIn) -> dict:
    mission_id = payload.mission_id
    if not store.mission_exists(mission_id):
        raise HTTPException(status_code=404, detail=f"mission not found: {mission_id}")
    record = payload.detection.model_dump(by_alias=True)
    try:
        validate_detection(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    store.add_detection(mission_id, record)
    record_event(mission_id, "DETECTION_RECEIVED", f"{record['class']} at confidence {record['confidence']:.2f}")
    await manager.broadcast(
        mission_id,
        {"type": "detection", "mission_id": mission_id, "data": record},
    )
    return record