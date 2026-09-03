"""
AetherSAR Phase 5 - backend API tests (FastAPI TestClient, no server needed).

Run: python3 -m backend.tests.test_backend
Covers missions, search paths, telemetry, detections, retrieval, error
handling, the end-to-end flow, and basic WebSocket connect/disconnect.
Live WebSocket event flow is covered by test_websocket_live.py.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fastapi.testclient import TestClient

from backend.main import app
from planner.search_area import SearchArea
from planner.search_planner import generate_lawnmower

client = TestClient(app)

AREA = {"min_lat": 18.5204, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599}
SPACING = 85.0


def _telemetry_record(mission_id: str, **overrides) -> dict:
    record = {
        "drone_id": "DRONE-01",
        "mission_id": mission_id,
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
    record.update(overrides)
    return record


def _detection_record(**overrides) -> dict:
    record = {
        "timestamp": "2026-09-03T16:53:43.235Z",
        "drone_id": "DRONE-01",
        "frame_id": 42,
        "class": "person",
        "confidence": 0.87,
        "bbox": {"x1": 120, "y1": 80, "x2": 250, "y2": 310},
    }
    record.update(overrides)
    return record


def _create_mission(name="Test mission") -> dict:
    response = client.post("/missions", json={"name": name, "search_area": AREA})
    assert response.status_code == 201, response.text
    return response.json()


# --------------------------------------------------------------------------
# Meta
# --------------------------------------------------------------------------

def test_health_and_root():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    print("PASS: GET / and /health")


# --------------------------------------------------------------------------
# Missions
# --------------------------------------------------------------------------

def test_create_and_get_mission():
    mission = _create_mission("Alpha")
    assert mission["mission_id"]
    assert mission["status"] == "created"
    assert mission["search_area"] == AREA
    assert mission["created_at"]
    fetched = client.get(f"/missions/{mission['mission_id']}")
    assert fetched.status_code == 200
    assert fetched.json() == mission
    print("PASS: POST /missions and GET /missions/{id}")


def test_get_unknown_mission_404():
    assert client.get("/missions/nope").status_code == 404
    print("PASS: GET unknown mission -> 404")


def test_create_mission_invalid_search_area():
    inverted = {"min_lat": 18.53, "min_lon": 73.85, "max_lat": 18.52, "max_lon": 73.86}
    response = client.post("/missions", json={"name": "bad", "search_area": inverted})
    assert response.status_code == 422, response.text
    out_of_range = dict(AREA, min_lat=95.0)
    response = client.post("/missions", json={"name": "oor", "search_area": out_of_range})
    assert response.status_code == 422, response.text
    # NaN literal: not expressible in strict JSON, but Python's parser accepts
    # it, so the SearchArea validation must still reject it at the API layer.
    raw_nan = (
        '{"name": "nan", "search_area": '
        '{"min_lat": NaN, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599}}'
    )
    response = client.post(
        "/missions", content=raw_nan, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422, response.text
    missing = client.post("/missions", json={"name": "missing"})
    assert missing.status_code == 422
    print("PASS: invalid search areas rejected with 422")


# --------------------------------------------------------------------------
# Search path
# --------------------------------------------------------------------------

def test_generate_and_get_search_path_uses_planner():
    mission = _create_mission()
    mid = mission["mission_id"]
    response = client.post(f"/missions/{mid}/search-path", json={"spacing_m": SPACING})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["mission_id"] == mid
    assert body["spacing_m"] == SPACING

    area = SearchArea.from_dict(AREA)
    expected = generate_lawnmower(area, SPACING)  # the actual Phase 4 planner
    assert body["waypoints"] == expected
    assert len(body["waypoints"]) > 4
    for waypoint in body["waypoints"]:
        assert set(waypoint.keys()) == {"latitude", "longitude"}
        assert area.contains(waypoint["latitude"], waypoint["longitude"])

    fetched = client.get(f"/missions/{mid}/search-path")
    assert fetched.status_code == 200
    assert fetched.json() == body
    print(f"PASS: search path generated by existing planner ({len(expected)} waypoints, canonical format)")


def test_search_path_not_generated_yet():
    mission = _create_mission()
    response = client.get(f"/missions/{mission['mission_id']}/search-path")
    assert response.status_code == 404
    print("PASS: GET search-path before generation -> 404")


def test_search_path_unknown_mission_404():
    assert client.post("/missions/nope/search-path", json={}).status_code == 404
    print("PASS: search-path for unknown mission -> 404")


def test_search_path_invalid_spacing():
    mission = _create_mission()
    mid = mission["mission_id"]
    for spacing in (0, -5):
        response = client.post(f"/missions/{mid}/search-path", json={"spacing_m": spacing})
        assert response.status_code == 422, f"spacing {spacing} -> {response.status_code}"
    raw_nan = '{"spacing_m": NaN}'
    response = client.post(
        f"/missions/{mid}/search-path", content=raw_nan, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422, response.text
    print("PASS: invalid spacing rejected with 422")


# --------------------------------------------------------------------------
# Telemetry
# --------------------------------------------------------------------------

def test_telemetry_valid_and_retrievable():
    mission = _create_mission()
    mid = mission["mission_id"]
    response = client.post("/telemetry", json=_telemetry_record(mid))
    assert response.status_code == 200, response.text
    stored = response.json()
    assert stored["source"] == "SIMULATED"
    fetched = client.get(f"/missions/{mid}/telemetry")
    assert fetched.status_code == 200
    assert fetched.json() == [stored]
    print("PASS: valid telemetry accepted and retrievable")


def test_telemetry_invalid_rejected():
    mission = _create_mission()
    mid = mission["mission_id"]
    cases = [
        _telemetry_record(mid, latitude=95.0),
        _telemetry_record(mid, battery_pct=-1.0),
        _telemetry_record(mid, source="REAL"),
        _telemetry_record(mid, current_waypoint=-3),
    ]
    for record in cases:
        response = client.post("/telemetry", json=record)
        assert response.status_code == 422, f"{record!r} -> {response.status_code}"
    # NaN longitude via a raw body (Python's JSON parser accepts the literal).
    nan_body = json.dumps(_telemetry_record(mid)).replace(
        '"longitude": 73.8567', '"longitude": NaN'
    )
    response = client.post(
        "/telemetry", content=nan_body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 422, response.text
    missing = _telemetry_record(mid)
    del missing["timestamp"]
    assert client.post("/telemetry", json=missing).status_code == 422
    print("PASS: invalid telemetry rejected with 422")


def test_telemetry_unknown_mission_404():
    response = client.post("/telemetry", json=_telemetry_record("no-such-mission"))
    assert response.status_code == 404
    print("PASS: telemetry for unknown mission -> 404")


def test_telemetry_empty_before_ingestion():
    mission = _create_mission()
    response = client.get(f"/missions/{mission['mission_id']}/telemetry")
    assert response.status_code == 200
    assert response.json() == []
    print("PASS: telemetry retrieval returns empty list before ingestion")


# --------------------------------------------------------------------------
# Detections
# --------------------------------------------------------------------------

def test_detection_valid_and_retrievable():
    mission = _create_mission()
    mid = mission["mission_id"]
    payload = {"mission_id": mid, "detection": _detection_record()}
    response = client.post("/detections", json=payload)
    assert response.status_code == 201, response.text
    stored = response.json()
    assert stored["class"] == "person"
    assert stored["bbox"] == {"x1": 120, "y1": 80, "x2": 250, "y2": 310}
    # No invented geolocation.
    assert "latitude" not in stored
    assert "longitude" not in stored
    fetched = client.get(f"/missions/{mid}/detections")
    assert fetched.status_code == 200
    assert fetched.json() == [stored]
    print("PASS: valid detection accepted (canonical 6 fields, no geo) and retrievable")


def test_detection_invalid_rejected():
    mission = _create_mission()
    mid = mission["mission_id"]
    bad_confidence = _detection_record(confidence=1.5)
    response = client.post("/detections", json={"mission_id": mid, "detection": bad_confidence})
    assert response.status_code == 422, response.text
    bad_bbox = _detection_record(bbox={"x1": 250, "y1": 80, "x2": 120, "y2": 310})
    response = client.post("/detections", json={"mission_id": mid, "detection": bad_bbox})
    assert response.status_code == 422, response.text
    missing_key = _detection_record()
    del missing_key["bbox"]["x2"]
    response = client.post("/detections", json={"mission_id": mid, "detection": missing_key})
    assert response.status_code == 422, response.text
    print("PASS: invalid detections rejected with 422")


def test_detection_unknown_mission_404():
    payload = {"mission_id": "no-such-mission", "detection": _detection_record()}
    assert client.post("/detections", json=payload).status_code == 404
    print("PASS: detection for unknown mission -> 404")


# --------------------------------------------------------------------------
# End-to-end flow
# --------------------------------------------------------------------------

def test_end_to_end_flow():
    mission = _create_mission("Full flow")
    mid = mission["mission_id"]

    path_response = client.post(f"/missions/{mid}/search-path", json={"spacing_m": SPACING})
    assert path_response.status_code == 200

    telemetry = client.post("/telemetry", json=_telemetry_record(mid))
    assert telemetry.status_code == 200

    detection = client.post("/detections", json={"mission_id": mid, "detection": _detection_record()})
    assert detection.status_code == 201

    assert client.get(f"/missions/{mid}").json()["mission_id"] == mid
    assert client.get(f"/missions/{mid}/search-path").json()["waypoints"]
    assert client.get(f"/missions/{mid}/telemetry").json() == [telemetry.json()]
    assert client.get(f"/missions/{mid}/detections").json() == [detection.json()]
    print("PASS: end-to-end flow (mission -> path -> telemetry -> detection -> retrieval)")


# --------------------------------------------------------------------------
# WebSocket (basic connect/disconnect; event flow is tested live)
# --------------------------------------------------------------------------

def test_websocket_connect_and_disconnect():
    mission = _create_mission()
    mid = mission["mission_id"]
    with client.websocket_connect(f"/ws/missions/{mid}") as websocket:
        websocket.send_text("ping")  # ignored by the server, connection stays open
    print("PASS: WebSocket connects and disconnects cleanly")


def run_all():
    print("Running backend API tests...\n")
    test_health_and_root()
    test_create_and_get_mission()
    test_get_unknown_mission_404()
    test_create_mission_invalid_search_area()
    test_generate_and_get_search_path_uses_planner()
    test_search_path_not_generated_yet()
    test_search_path_unknown_mission_404()
    test_search_path_invalid_spacing()
    test_telemetry_valid_and_retrievable()
    test_telemetry_invalid_rejected()
    test_telemetry_unknown_mission_404()
    test_telemetry_empty_before_ingestion()
    test_detection_valid_and_retrievable()
    test_detection_invalid_rejected()
    test_detection_unknown_mission_404()
    test_end_to_end_flow()
    test_websocket_connect_and_disconnect()
    print("\nAll backend API tests passed.")


if __name__ == "__main__":
    run_all()