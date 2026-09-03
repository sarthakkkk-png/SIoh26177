"""Tests for planner.coordinates - WGS84 coordinate validation."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planner.coordinates import (
    MAX_LATITUDE,
    MAX_LONGITUDE,
    MIN_LATITUDE,
    MIN_LONGITUDE,
    validate_latitude,
    validate_longitude,
    validate_lat_lon,
)


def _expect_value_error(function, value):
    try:
        function(value)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for {value!r}")


def test_valid_coordinates_accepted():
    assert validate_latitude(18.5204) == 18.5204
    assert validate_longitude(73.8567) == 73.8567
    lat, lon = validate_lat_lon(18.5204, 73.8567)
    assert (lat, lon) == (18.5204, 73.8567)
    print("PASS: valid coordinates accepted")


def test_numeric_strings_accepted():
    assert validate_latitude("18.52") == 18.52
    assert validate_longitude("73.85") == 73.85
    print("PASS: numeric strings accepted")


def test_boundary_values_accepted():
    assert validate_latitude(MIN_LATITUDE) == -90.0
    assert validate_latitude(MAX_LATITUDE) == 90.0
    assert validate_longitude(MIN_LONGITUDE) == -180.0
    assert validate_longitude(MAX_LONGITUDE) == 180.0
    print("PASS: boundary values accepted")


def test_nan_latitude_rejected():
    for bad in (float("nan"), "nan"):
        _expect_value_error(validate_latitude, bad)
    print("PASS: NaN latitude rejected")


def test_nan_longitude_rejected():
    for bad in (float("nan"), "nan"):
        _expect_value_error(validate_longitude, bad)
    print("PASS: NaN longitude rejected")


def test_infinity_rejected():
    for bad in (float("inf"), float("-inf"), "inf"):
        _expect_value_error(validate_latitude, bad)
        _expect_value_error(validate_longitude, bad)
    print("PASS: infinity rejected")


def test_out_of_range_latitude_rejected():
    for bad in (-90.0001, 90.0001, -95.0, 95.0):
        _expect_value_error(validate_latitude, bad)
    print("PASS: out-of-range latitude rejected")


def test_out_of_range_longitude_rejected():
    for bad in (-180.0001, 180.0001, -200.0, 200.0):
        _expect_value_error(validate_longitude, bad)
    print("PASS: out-of-range longitude rejected")


def test_malformed_values_rejected():
    for bad in (None, "abc", [], True):
        _expect_value_error(validate_latitude, bad)
        _expect_value_error(validate_longitude, bad)
    print("PASS: malformed values rejected")


def run_all():
    print("Running coordinate validation tests...\n")
    test_valid_coordinates_accepted()
    test_numeric_strings_accepted()
    test_boundary_values_accepted()
    test_nan_latitude_rejected()
    test_nan_longitude_rejected()
    test_infinity_rejected()
    test_out_of_range_latitude_rejected()
    test_out_of_range_longitude_rejected()
    test_malformed_values_rejected()
    print("\nAll coordinate tests passed.")


if __name__ == "__main__":
    run_all()