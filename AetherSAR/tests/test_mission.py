"""Tests for simulator.mission - mission engine, battery/RTH behavior, and
search-area -> planner -> simulator integration."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from planner.search_area import SearchArea
from planner.search_planner import generate_lawnmower
from simulator.drone import BATTERY_CRITICAL, DroneState
from simulator.mission import execute_mission
from simulator.path_follower import WAYPOINT_REACH_THRESHOLD_M, haversine_distance_m
from simulator.telemetry import validate_telemetry
from simulator.waypoints import load_waypoints

LEGACY_FILE = Path(__file__).resolve().parents[1] / "simulator" / "waypoints.json"
AREA = SearchArea(min_lat=18.5204, min_lon=73.8567, max_lat=18.5228, max_lon=73.8599)


def _run(waypoints, battery=100.0, tick_delay=0.0):
    records = []
    drone = DroneState(
        latitude=waypoints[0]["latitude"],
        longitude=waypoints[0]["longitude"],
        battery_pct=battery,
        status="TAKEOFF",
    )
    drone = execute_mission(drone, waypoints, tick_delay=tick_delay, on_telemetry=records.append)
    return drone, records


def test_mission_completes_legacy_waypoints():
    waypoints = load_waypoints(LEGACY_FILE)
    drone, records = _run(waypoints)
    assert drone.status == "MISSION_COMPLETE"
    assert drone.current_waypoint == len(waypoints)
    assert records[0]["status"] == "TAKEOFF"
    assert records[-1]["status"] == "MISSION_COMPLETE"
    for record in records:
        validate_telemetry(record)
        assert record["source"] == "SIMULATED"
    assert drone.latitude == waypoints[-1]["latitude"]
    assert drone.longitude == waypoints[-1]["longitude"]
    assert 0 < drone.battery_pct < 100
    print("PASS: legacy waypoint mission completes with valid telemetry")


def test_search_area_planner_mission_integration():
    waypoints = generate_lawnmower(AREA, 85.0)
    drone, records = _run(waypoints)
    assert drone.status == "MISSION_COMPLETE"
    assert len(records) == len(waypoints) + 1  # TAKEOFF + (len-1) arrivals + MISSION_COMPLETE
    for record in records:
        validate_telemetry(record)
        assert AREA.contains(record["latitude"], record["longitude"])
    assert drone.battery_pct > 0
    print(
        f"PASS: search area -> planner -> simulator -> telemetry "
        f"({len(waypoints)} waypoints, {len(records)} records, battery {drone.battery_pct:.1f}%)"
    )


def test_mission_requires_waypoints():
    try:
        execute_mission(DroneState(), [])
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for empty waypoint list")
    print("PASS: empty waypoint list rejected")


def test_mission_rejects_invalid_waypoints():
    bad = [{"latitude": float("nan"), "longitude": 73.85}]
    try:
        execute_mission(DroneState(), bad)
    except ValueError:
        pass
    else:
        raise AssertionError("expected ValueError for NaN waypoint")
    print("PASS: invalid waypoints rejected by mission engine")


def test_low_battery_returns_home():
    waypoints = load_waypoints(LEGACY_FILE)
    drone, records = _run(waypoints, battery=15.5)  # crosses critical mid-flight
    statuses = [record["status"] for record in records]
    assert "LOW_BATTERY" in statuses
    assert "RTH" in statuses
    assert drone.status == "STOPPED"
    assert "MISSION_COMPLETE" not in statuses
    assert drone.battery_pct >= 0
    home = waypoints[0]
    distance = haversine_distance_m(
        drone.latitude, drone.longitude, home["latitude"], home["longitude"]
    )
    assert distance <= WAYPOINT_REACH_THRESHOLD_M + 1e-6
    print("PASS: simulated RTH at critical battery, drone stops near home")


def test_critical_battery_triggers_immediate_rth():
    waypoints = load_waypoints(LEGACY_FILE)
    drone, records = _run(waypoints, battery=BATTERY_CRITICAL)
    assert records[0]["status"] == "TAKEOFF"
    assert records[1]["status"] == "LOW_BATTERY"
    assert drone.status == "STOPPED"
    assert "MISSION_COMPLETE" not in [r["status"] for r in records]
    print("PASS: critical battery triggers LOW_BATTERY then immediate RTH")


def test_battery_never_depletes_below_zero():
    waypoints = load_waypoints(LEGACY_FILE)
    drone, records = _run(waypoints, battery=BATTERY_CRITICAL)
    assert all(record["battery_pct"] >= 0 for record in records)
    print("PASS: telemetry battery_pct never negative")


def run_all():
    print("Running mission/integration tests...\n")
    test_mission_completes_legacy_waypoints()
    test_search_area_planner_mission_integration()
    test_mission_requires_waypoints()
    test_mission_rejects_invalid_waypoints()
    test_low_battery_returns_home()
    test_critical_battery_triggers_immediate_rth()
    test_battery_never_depletes_below_zero()
    print("\nAll mission/integration tests passed.")


if __name__ == "__main__":
    run_all()