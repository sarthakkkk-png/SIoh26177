"""Tests for planner.search_area - SearchArea bounding-box abstraction."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planner.search_area import SearchArea


def _expect_value_error(builder):
    try:
        builder()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_valid_area_from_dict():
    area = SearchArea.from_dict(
        {"min_lat": 18.52, "min_lon": 73.85, "max_lat": 18.53, "max_lon": 73.86}
    )
    assert area.min_lat == 18.52
    assert area.min_lon == 73.85
    assert area.max_lat == 18.53
    assert area.max_lon == 73.86
    print("PASS: valid area from dict")


def test_min_lat_ge_max_lat_rejected():
    _expect_value_error(lambda: SearchArea(18.53, 73.85, 18.52, 73.86))
    _expect_value_error(lambda: SearchArea(18.52, 73.85, 18.52, 73.86))
    print("PASS: min_lat >= max_lat rejected")


def test_min_lon_ge_max_lon_rejected():
    _expect_value_error(lambda: SearchArea(18.52, 73.86, 18.53, 73.85))
    _expect_value_error(lambda: SearchArea(18.52, 73.85, 18.53, 73.85))
    print("PASS: min_lon >= max_lon rejected")


def test_nan_rejected():
    _expect_value_error(lambda: SearchArea(float("nan"), 73.85, 18.53, 73.86))
    _expect_value_error(lambda: SearchArea(18.52, 73.85, float("nan"), 73.86))
    print("PASS: NaN rejected")


def test_out_of_range_rejected():
    _expect_value_error(lambda: SearchArea(95.0, 73.85, 18.53, 73.86))
    _expect_value_error(lambda: SearchArea(18.52, 200.0, 18.53, 73.86))
    print("PASS: out-of-range coordinates rejected")


def test_missing_dict_key_rejected():
    _expect_value_error(lambda: SearchArea.from_dict({"min_lat": 18.52}))
    _expect_value_error(lambda: SearchArea.from_dict({}))
    print("PASS: missing dict key rejected")


def test_metric_size_approximation():
    import math

    area = SearchArea(0.0, 0.0, 1.0, 1.0)
    assert abs(area.height_m - 111_320.0) < 1.0
    # Width is scaled by cos(center_latitude); center is at 0.5 deg here.
    expected_width = 111_320.0 * math.cos(math.radians(area.center_lat))
    assert abs(area.width_m - expected_width) < 1.0
    assert area.height_m > 0 and area.width_m > 0
    print("PASS: metric size approximation (1 deg ~ 111,320 m)")


def test_contains():
    area = SearchArea(18.52, 73.85, 18.53, 73.86)
    assert area.contains(18.525, 73.855)
    assert not area.contains(18.51, 73.855)
    assert not area.contains(18.525, 73.87)
    print("PASS: contains() boundary checks")


def test_to_dict_roundtrip():
    area = SearchArea(18.52, 73.85, 18.53, 73.86)
    assert SearchArea.from_dict(area.to_dict()) == area
    print("PASS: to_dict/from_dict roundtrip")


def run_all():
    print("Running search-area tests...\n")
    test_valid_area_from_dict()
    test_min_lat_ge_max_lat_rejected()
    test_min_lon_ge_max_lon_rejected()
    test_nan_rejected()
    test_out_of_range_rejected()
    test_missing_dict_key_rejected()
    test_metric_size_approximation()
    test_contains()
    test_to_dict_roundtrip()
    print("\nAll search-area tests passed.")


if __name__ == "__main__":
    run_all()