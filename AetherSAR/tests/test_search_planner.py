"""Tests for planner.search_planner - lawnmower search-path generation."""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planner.search_area import SearchArea, M_PER_DEG_LAT
from planner.search_planner import generate_lawnmower

AREA = SearchArea(min_lat=18.5204, min_lon=73.8567, max_lat=18.5228, max_lon=73.8599)
SPACING = 85.0


def _split_tracks(waypoints):
    """Split a waypoint list into per-track segments (tracks share latitude)."""
    tracks = []
    current = [waypoints[0]]
    for waypoint in waypoints[1:]:
        if waypoint["latitude"] == current[-1]["latitude"]:
            current.append(waypoint)
        else:
            tracks.append(current)
            current = [waypoint]
    tracks.append(current)
    return tracks


def _expect_value_error(function):
    try:
        function()
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_requires_search_area():
    try:
        generate_lawnmower("not-an-area", SPACING)
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError for non-SearchArea input")
    print("PASS: requires a SearchArea")


def test_invalid_spacing_rejected():
    for bad in (0, -5, float("nan"), float("inf"), "abc", True):
        _expect_value_error(lambda b=bad: generate_lawnmower(AREA, b))
    print("PASS: invalid spacing rejected")


def test_deterministic_output():
    assert generate_lawnmower(AREA, SPACING) == generate_lawnmower(AREA, SPACING)
    print("PASS: deterministic output")


def test_all_waypoints_inside_area():
    for waypoint in generate_lawnmower(AREA, SPACING):
        assert AREA.contains(waypoint["latitude"], waypoint["longitude"])
    print("PASS: all waypoints inside the search area")


def test_no_consecutive_duplicates():
    waypoints = generate_lawnmower(AREA, SPACING)
    for previous, current in zip(waypoints, waypoints[1:]):
        assert previous != current
    print("PASS: no consecutive duplicate waypoints")


def test_first_waypoint_is_southwest_corner():
    first = generate_lawnmower(AREA, SPACING)[0]
    assert first == {"latitude": AREA.min_lat, "longitude": AREA.min_lon}
    print("PASS: first waypoint is the southwest corner")


def test_waypoint_count_matches_grid():
    expected = (
        math.ceil(AREA.height_m / SPACING) + 1
    ) * (math.ceil(AREA.width_m / SPACING) + 1)
    assert len(generate_lawnmower(AREA, SPACING)) == expected
    print(f"PASS: waypoint count matches grid ({expected} waypoints)")


def test_alternating_lawnmower_direction():
    tracks = _split_tracks(generate_lawnmower(AREA, SPACING))
    assert len(tracks) >= 2
    for index, track in enumerate(tracks):
        longitudes = [point["longitude"] for point in track]
        if index % 2 == 0:
            assert longitudes == sorted(longitudes), "even track must go eastward"
        else:
            assert longitudes == sorted(longitudes, reverse=True), "odd track must go westward"
        assert len(set(longitudes)) == len(longitudes), "track must be strictly monotonic"
    print("PASS: alternating lawnmower direction")


def test_track_spacing_respected():
    tracks = _split_tracks(generate_lawnmower(AREA, SPACING))
    latitudes = [track[0]["latitude"] for track in tracks]
    gaps_m = [
        (high - low) * M_PER_DEG_LAT for low, high in zip(latitudes, latitudes[1:])
    ]
    assert all(gap > 0 for gap in gaps_m)
    assert max(gaps_m) <= SPACING + 1e-6
    print(f"PASS: track spacing <= requested spacing (max gap {max(gaps_m):.1f} m)")


def test_small_area():
    small = SearchArea(18.52, 73.85, 18.5202, 73.8502)
    waypoints = generate_lawnmower(small, 5.0)
    assert len(waypoints) > 4
    for waypoint in waypoints:
        assert small.contains(waypoint["latitude"], waypoint["longitude"])
    assert len(set(map(str, waypoints))) == len(waypoints)
    print(f"PASS: small area handled ({len(waypoints)} waypoints, all inside)")


def test_very_large_spacing():
    waypoints = generate_lawnmower(AREA, 1e9)
    assert len(waypoints) == 4
    for waypoint in waypoints:
        assert AREA.contains(waypoint["latitude"], waypoint["longitude"])
    assert waypoints[0] == {"latitude": AREA.min_lat, "longitude": AREA.min_lon}
    print("PASS: very large spacing collapses to the four corners")


def run_all():
    print("Running search-planner tests...\n")
    test_requires_search_area()
    test_invalid_spacing_rejected()
    test_deterministic_output()
    test_all_waypoints_inside_area()
    test_no_consecutive_duplicates()
    test_first_waypoint_is_southwest_corner()
    test_waypoint_count_matches_grid()
    test_alternating_lawnmower_direction()
    test_track_spacing_respected()
    test_small_area()
    test_very_large_spacing()
    print("\nAll search-planner tests passed.")


if __name__ == "__main__":
    run_all()