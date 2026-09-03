"""Tests for simulator.waypoints - waypoint file loading and validation."""

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from simulator.waypoints import load_waypoints, validate_waypoint

LEGACY_FILE = Path(__file__).resolve().parents[1] / "simulator" / "waypoints.json"


def _write_waypoints(payload) -> Path:
    file = Path(tempfile.mktemp(suffix=".json"))
    file.write_text(json.dumps(payload), encoding="utf-8")
    return file


def _expect_value_error(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_legacy_waypoints_load():
    waypoints = load_waypoints(LEGACY_FILE)
    assert len(waypoints) == 8
    assert waypoints[0] == {"latitude": 18.5204, "longitude": 73.8567}
    assert waypoints[-1] == {"latitude": 18.5228, "longitude": 73.8599}
    assert all(isinstance(wp["latitude"], float) and isinstance(wp["longitude"], float) for wp in waypoints)
    print("PASS: legacy waypoints.json loads (8 waypoints)")


def test_valid_waypoint_normalized():
    normalized = validate_waypoint({"latitude": "18.52", "longitude": 73.85, "extra": "ignored"})
    assert normalized == {"latitude": 18.52, "longitude": 73.85}
    print("PASS: valid waypoint normalized to floats")


def test_missing_latitude_rejected():
    _expect_value_error(lambda: validate_waypoint({"longitude": 73.85}))
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"longitude": 73.85}])))
    print("PASS: missing latitude rejected")


def test_missing_longitude_rejected():
    _expect_value_error(lambda: validate_waypoint({"latitude": 18.52}))
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": 18.52}])))
    print("PASS: missing longitude rejected")


def test_nan_latitude_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": float("nan"), "longitude": 73.85}])))
    print("PASS: NaN latitude rejected")


def test_nan_longitude_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": 18.52, "longitude": float("nan")}])))
    print("PASS: NaN longitude rejected")


def test_out_of_range_latitude_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": 95.0, "longitude": 73.85}])))
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": -95.0, "longitude": 73.85}])))
    print("PASS: out-of-range latitude rejected")


def test_out_of_range_longitude_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": 18.52, "longitude": 200.0}])))
    _expect_value_error(lambda: load_waypoints(_write_waypoints([{"latitude": 18.52, "longitude": -200.0}])))
    print("PASS: out-of-range longitude rejected")


def test_malformed_waypoint_rejected():
    _expect_value_error(lambda: validate_waypoint([18.52, 73.85]))
    _expect_value_error(lambda: load_waypoints(_write_waypoints([[18.52, 73.85]])))
    print("PASS: malformed waypoint (non-dict) rejected")


def test_non_list_json_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints({"latitude": 18.52})))
    print("PASS: non-list JSON rejected")


def test_empty_list_rejected():
    _expect_value_error(lambda: load_waypoints(_write_waypoints([])))
    print("PASS: empty waypoint list rejected")


def test_missing_file_rejected():
    try:
        load_waypoints(Path(tempfile.mktemp(suffix=".json")))
    except FileNotFoundError:
        pass
    else:
        raise AssertionError("expected FileNotFoundError")
    print("PASS: missing file rejected")


def run_all():
    print("Running waypoint validation tests...\n")
    test_legacy_waypoints_load()
    test_valid_waypoint_normalized()
    test_missing_latitude_rejected()
    test_missing_longitude_rejected()
    test_nan_latitude_rejected()
    test_nan_longitude_rejected()
    test_out_of_range_latitude_rejected()
    test_out_of_range_longitude_rejected()
    test_malformed_waypoint_rejected()
    test_non_list_json_rejected()
    test_empty_list_rejected()
    test_missing_file_rejected()
    print("\nAll waypoint validation tests passed.")


if __name__ == "__main__":
    run_all()