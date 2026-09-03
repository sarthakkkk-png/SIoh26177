"""
AetherSAR Phase 5 - telemetry ingestion.

Mission association: the canonical telemetry record carries `mission_id`
(simulator.telemetry.TELEMETRY_FIELDS); that field is the association key,
so no wrapper or renamed fields are needed. The mission must already exist
(POST /missions) - orphan records are rejected so the mission-centric API
stays consistent.

Validation uses the EXISTING simulator.telemetry.validate_telemetry; invalid
records are rejected with 422 rather than silently accepted.
"""

from fastapi import APIRouter, HTTPException

from backend.schemas import TelemetryRecord
from backend.store import store
from backend.websocket import manager
from simulator.telemetry import validate_telemetry

router = APIRouter(tags=["telemetry"])


@router.post("/telemetry", response_model=TelemetryRecord)
async def ingest_telemetry(payload: TelemetryRecord) -> dict:
    mission_id = payload.mission_id
    if not store.mission_exists(mission_id):
        raise HTTPException(status_code=404, detail=f"mission not found: {mission_id}")
    record = payload.model_dump()
    try:
        validate_telemetry(record)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    store.add_telemetry(mission_id, record)
    await manager.broadcast(
        mission_id,
        {"type": "telemetry", "mission_id": mission_id, "data": record},
    )
    return record