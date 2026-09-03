"""
AetherSAR Phase 5/6 - FastAPI backend.

Local prototype backend exposing missions, search paths, telemetry,
detections, and a WebSocket event stream. Persistence is handled by a
store facade (backend/store.py): Supabase/PostgreSQL when SUPABASE_URL and
SUPABASE_KEY are configured, otherwise the in-memory fallback so the
backend runs fully offline. All flight data is SIMULATED and clearly
labelled.

Start (from the AetherSAR/ directory):

    python3 -m uvicorn backend.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.database.repositories import PersistenceError
from backend.routes import detections, missions, telemetry
from backend.store import persistence_mode
from backend.websocket import router as websocket_router

app = FastAPI(
    title="AetherSAR Backend",
    description=(
        "Simulated search-and-rescue mission backend. All flight data is "
        "SIMULATED; detections carry no geographic coordinates (geolocation "
        "is not implemented). Persistence uses Supabase when configured and "
        "an in-memory store otherwise."
    ),
    version="0.1.0",
)

app.include_router(missions.router)
app.include_router(telemetry.router)
app.include_router(detections.router)
app.include_router(websocket_router)


@app.exception_handler(PersistenceError)
async def persistence_error_handler(request: Request, exc: PersistenceError) -> JSONResponse:
    """Surface database failures clearly instead of hiding them."""
    return JSONResponse(status_code=500, content={"detail": f"persistence error: {exc}"})


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "AetherSAR Backend",
        "status": "ok",
        "persistence": persistence_mode(),
        "docs": "/docs",
    }


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok"}