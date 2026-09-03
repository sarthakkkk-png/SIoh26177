"""
AetherSAR Phase 5 - live WebSocket event-flow test.

Starts a real uvicorn server in a subprocess, connects a real WebSocket
client, ingests telemetry through the HTTP API, and asserts the event is
broadcast over the socket. This exercises the actual server stack rather
than the in-process TestClient.

Run: python3 -m backend.tests.test_websocket_live
"""

import asyncio
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx
import websockets

ROOT = Path(__file__).resolve().parents[2]

AREA = {"min_lat": 18.5204, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599}


def _pick_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _wait_for_health(proc, base_url: str, timeout: float = 15.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"uvicorn exited early with code {proc.returncode}")
        try:
            with httpx.Client(base_url=base_url, timeout=1.0) as client:
                response = client.get("/health")
            if response.status_code == 200 and response.json() == {"status": "ok"}:
                return
        except Exception:
            pass
        time.sleep(0.25)
    raise RuntimeError("server did not become healthy in time")


def test_websocket_live_event_flow() -> None:
    port = _pick_port()
    base_url = f"http://127.0.0.1:{port}"
    ws_url = f"ws://127.0.0.1:{port}"

    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "backend.main:app",
            "--port",
            str(port),
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        _wait_for_health(proc, base_url)

        with httpx.Client(base_url=base_url, timeout=5.0) as client:
            mission = client.post(
                "/missions", json={"name": "ws flow", "search_area": AREA}
            ).json()

        record = {
            "drone_id": "DRONE-01",
            "mission_id": mission["mission_id"],
            "timestamp": "2026-09-03T16:53:43.235Z",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "altitude_m": 80.0,
            "heading_deg": 90.0,
            "speed_mps": 8.0,
            "battery_pct": 95.0,
            "status": "SEARCHING",
            "current_waypoint": 1,
            "total_waypoints": 25,
            "source": "SIMULATED",
        }

        async def _flow() -> dict:
            async with websockets.connect(f"{ws_url}/ws/missions/{mission['mission_id']}") as ws:
                async with httpx.AsyncClient(base_url=base_url) as http:
                    response = await http.post("/telemetry", json=record)
                    assert response.status_code == 200, response.text
                raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
                return json.loads(raw)

        event = asyncio.run(_flow())
        assert event["type"] == "telemetry"
        assert event["mission_id"] == mission["mission_id"]
        assert event["data"]["source"] == "SIMULATED"
        print("PASS: live WebSocket received the telemetry broadcast")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    test_websocket_live_event_flow()
    print("Live WebSocket test passed.")