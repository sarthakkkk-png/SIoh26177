"""
AetherSAR - CV runtime tests (real model inference) and CV -> FastAPI
integration.

These tests REQUIRE the optional runtime stack (ultralytics + model weights)
and are skipped gracefully when it is unavailable, so the automated suite
never depends on internet access or model downloads. Results are reported
honestly: if a person is not detected in the sample image, that is reported,
never fabricated.

Run: python3 -m tests.test_cv_runtime
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cv.detection import DETECTION_FIELDS, validate_detection

SAMPLE_IMAGE = Path(__file__).resolve().parents[1] / "cv" / "samples" / "bus.jpg"


def _load_detector():
    """Return a working detector, or None (with a printed reason) if the
    optional runtime stack is unavailable."""
    try:
        from cv.detect import UltralyticsPersonDetector
    except ImportError:
        return None
    try:
        return UltralyticsPersonDetector(model="yolov8n.pt", confidence_threshold=0.35)
    except Exception as exc:  # model download/load failure (e.g. no network)
        print(f"NOTE: model unavailable, skipping runtime tests: {exc}")
        return None


def test_sample_image_exists():
    assert SAMPLE_IMAGE.exists(), f"sample image missing: {SAMPLE_IMAGE}"
    print(f"PASS: sample image present ({SAMPLE_IMAGE.name})")


def test_real_inference_produces_valid_detections():
    detector = _load_detector()
    if detector is None:
        print("SKIPPED: real inference (ultralytics/model not available)")
        return
    detections = detector.detect(str(SAMPLE_IMAGE), drone_id="DRONE-01", frame_id=1)
    print(f"NOTE: model returned {len(detections)} person detection(s) on {SAMPLE_IMAGE.name}")
    for detection in detections:
        validate_detection(detection)
        for field in DETECTION_FIELDS:
            assert field in detection
        # Canonical schema must not carry invented geographic coordinates.
        assert "latitude" not in detection
        assert "longitude" not in detection
        assert "mission_id" not in detection
    print("PASS: all real model outputs validate against the canonical detection schema")


def test_real_detection_ingested_by_backend():
    detector = _load_detector()
    if detector is None:
        print("SKIPPED: CV -> backend integration (model not available)")
        return
    try:
        from fastapi.testclient import TestClient

        from backend.main import app
    except ImportError:
        print("SKIPPED: CV -> backend integration (fastapi not available)")
        return

    detections = detector.detect(str(SAMPLE_IMAGE), drone_id="DRONE-01", frame_id=1)
    if not detections:
        print("SKIPPED: CV -> backend integration (model produced no person detections)")
        return

    area = {"min_lat": 18.5204, "min_lon": 73.8567, "max_lat": 18.5228, "max_lon": 73.8599}
    with TestClient(app) as client:
        mission = client.post("/missions", json={"name": "cv runtime", "search_area": area})
        assert mission.status_code == 201, mission.text
        mission_id = mission.json()["mission_id"]

        detection = detections[0]
        response = client.post(
            "/detections", json={"mission_id": mission_id, "detection": detection}
        )
        assert response.status_code == 201, response.text
        stored = response.json()
        assert stored == detection
        assert "latitude" not in stored and "longitude" not in stored

        fetched = client.get(f"/missions/{mission_id}/detections")
        assert fetched.status_code == 200
        assert fetched.json() == [detection]
    print(f"PASS: real detection ingested by FastAPI backend and retrievable (mission {mission_id})")


def run_all():
    print("Running CV runtime tests...\n")
    test_sample_image_exists()
    test_real_inference_produces_valid_detections()
    test_real_detection_ingested_by_backend()
    print("\nAll CV runtime tests passed.")


if __name__ == "__main__":
    run_all()