"""Tests for cv.detection and cv.detect - detection schema and detector interface.

These tests do not require model weights or the optional ultralytics package.
No detection accuracy or frame-rate figures are claimed anywhere.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cv.detection import (
    DETECTION_FIELDS,
    build_detection,
    validate_detection,
    validate_confidence,
)
from cv.detect import BaseDetector, BackendUnavailable, UltralyticsPersonDetector


def _valid_bbox():
    return {"x1": 120, "y1": 80, "x2": 250, "y2": 310}


def _expect_value_error(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_build_detection_has_all_fields():
    detection = build_detection(
        frame_id=42, class_name="person", confidence=0.87, bbox=_valid_bbox()
    )
    for field in DETECTION_FIELDS:
        assert field in detection
    assert detection["drone_id"] == "DRONE-01"
    assert detection["class"] == "person"
    assert detection["confidence"] == 0.87
    assert detection["bbox"] == {"x1": 120, "y1": 80, "x2": 250, "y2": 310}
    assert isinstance(detection["timestamp"], str) and detection["timestamp"]
    assert isinstance(detection["frame_id"], int)
    print("PASS: canonical detection record has all required fields")


def test_no_geographic_fields_invented():
    detection = build_detection(frame_id=1, class_name="person", confidence=0.9, bbox=_valid_bbox())
    assert "latitude" not in detection
    assert "longitude" not in detection
    print("PASS: no invented geographic coordinates in detection record")


def test_custom_timestamp_and_drone_id():
    detection = build_detection(
        drone_id="DRONE-07",
        frame_id=3,
        class_name="person",
        confidence=0.5,
        bbox=_valid_bbox(),
        timestamp="2026-09-03T10:00:00.000Z",
    )
    assert detection["drone_id"] == "DRONE-07"
    assert detection["timestamp"] == "2026-09-03T10:00:00.000Z"
    print("PASS: custom timestamp and drone_id")


def test_confidence_bounds():
    assert validate_confidence(0.0) == 0.0
    assert validate_confidence(1.0) == 1.0
    for bad in (-0.1, 1.1, float("nan"), float("inf"), True):
        _expect_value_error(lambda b=bad: validate_confidence(b))
    print("PASS: confidence bounds validated")


def test_frame_id_validation():
    for bad in (-1, 1.5, True, "2"):
        _expect_value_error(
            lambda b=bad: build_detection(frame_id=b, class_name="person", confidence=0.5, bbox=_valid_bbox())
        )
    print("PASS: frame_id must be a non-negative integer")


def test_class_and_drone_id_required():
    _expect_value_error(
        lambda: build_detection(frame_id=1, class_name="", confidence=0.5, bbox=_valid_bbox())
    )
    _expect_value_error(
        lambda: build_detection(drone_id="", frame_id=1, class_name="person", confidence=0.5, bbox=_valid_bbox())
    )
    print("PASS: class and drone_id must be non-empty strings")


def test_bbox_validation():
    missing_x2 = {"x1": 1, "y1": 1, "y2": 5}
    _expect_value_error(
        lambda: build_detection(frame_id=1, class_name="person", confidence=0.5, bbox=missing_x2)
    )
    inverted_x = {"x1": 250, "y1": 80, "x2": 120, "y2": 310}
    _expect_value_error(
        lambda: build_detection(frame_id=1, class_name="person", confidence=0.5, bbox=inverted_x)
    )
    inverted_y = {"x1": 120, "y1": 310, "x2": 250, "y2": 80}
    _expect_value_error(
        lambda: build_detection(frame_id=1, class_name="person", confidence=0.5, bbox=inverted_y)
    )
    negative = {"x1": -1, "y1": 0, "x2": 10, "y2": 10}
    _expect_value_error(
        lambda: build_detection(frame_id=1, class_name="person", confidence=0.5, bbox=negative)
    )
    print("PASS: malformed bbox rejected")


def test_missing_field_rejected():
    _expect_value_error(lambda: validate_detection({"timestamp": "2026-09-03T10:00:00Z"}))
    print("PASS: detection missing required fields rejected")


def test_ultralytics_backend_reports_unavailable():
    try:
        UltralyticsPersonDetector()
    except BackendUnavailable:
        pass
    else:
        # If ultralytics IS installed, this environment can run real inference;
        # the interface contract is still satisfied.
        print("NOTE: ultralytics is installed - runtime inference available here")
        return
    print("PASS: BackendUnavailable raised when ultralytics is missing")


class _FakeDetector(BaseDetector):
    """Test double implementing the detector interface (no model involved)."""

    def __init__(self):
        self.calls = 0

    def detect(self, image, *, drone_id="DRONE-01", frame_id=0):
        self.calls += 1
        return [
            build_detection(
                drone_id=drone_id,
                frame_id=frame_id,
                class_name="person",
                confidence=0.9,
                bbox=_valid_bbox(),
            )
        ]


def test_detector_interface_contract():
    detector = _FakeDetector()
    results = detector.detect("synthetic-input.png", drone_id="DRONE-01", frame_id=7)
    assert detector.calls == 1
    assert isinstance(results, list)
    for detection in results:
        validate_detection(detection)
        assert detection["frame_id"] == 7
    print("PASS: detector interface returns validated detection records")


def test_detector_interface_empty_result_is_valid():
    class _EmptyDetector(BaseDetector):
        def detect(self, image, *, drone_id="DRONE-01", frame_id=0):
            return []

    assert _EmptyDetector().detect("anything.png") == []
    print("PASS: empty detection list is a valid result")


def run_all():
    print("Running detection schema/interface tests...\n")
    test_build_detection_has_all_fields()
    test_no_geographic_fields_invented()
    test_custom_timestamp_and_drone_id()
    test_confidence_bounds()
    test_frame_id_validation()
    test_class_and_drone_id_required()
    test_bbox_validation()
    test_missing_field_rejected()
    test_ultralytics_backend_reports_unavailable()
    test_detector_interface_contract()
    test_detector_interface_empty_result_is_valid()
    print("\nAll detection tests passed.")


if __name__ == "__main__":
    run_all()