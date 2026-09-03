"""
AetherSAR Phase 5 - FastAPI backend.

Local prototype backend exposing missions, search paths, telemetry,
detections, and a WebSocket event stream. Storage is in-memory; there is
no database. All flight data is SIMULATED and clearly labelled.

Start (from the AetherSAR/ directory):

    python3 -m uvicorn backend.main:app --reload
"""

from fastapi import FastAPI

from backend.routes import detections, missions, telemetry
from backend.websocket import router as websocket_router

app = FastAPI(
    title="AetherSAR Backend",
    description=(
        "Simulated search-and-rescue mission backend. All flight data is "
        "SIMULATED; detections carry no geographic coordinates (geolocation "
        "is not implemented). Storage is in-memory and resets on restart."
    ),
    version="0.1.0",
)

app.include_router(missions.router)
app.include_router(telemetry.router)
app.include_router(detections.router)
app.include_router(websocket_router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {"name": "AetherSAR Backend", "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}