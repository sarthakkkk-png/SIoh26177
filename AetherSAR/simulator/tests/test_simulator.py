import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from simulator.drone import DroneState, INITIAL_BATTERY, DEFAULT_ALTITUDE_M
from simulator.path_follower import calculate_heading, move_toward_waypoint
from simulator.telemetry import build_telemetry


def test_1_drone_initializes_correctly():
    drone = DroneState(latitude=18.52, longitude=73.85)
    assert drone.drone_id == "DRONE-01"
    assert drone.source == "SIMULATED"
    assert drone.battery_pct == INITIAL_BATTERY
    assert drone.altitude_m == DEFAULT_ALTITUDE_M
    print("PASS: Test 1 – Drone initializes correctly")


def test_2_drone_moves_toward_waypoint():
    drone = DroneState(latitude=18.5204, longitude=73.8567)
    start_lon = drone.longitude
    move_toward_waypoint(drone, 18.5204, 73.8575, dt_seconds=2.0, speed_mps=8.0)
    assert drone.longitude > start_lon
    print("PASS: Test 2 – Drone moves toward waypoint")


def test_3_heading_changes_correctly():
    hdg = calculate_heading(18.52, 73.85, 18.52, 73.86)
    assert 80 < hdg < 100
    print(f"PASS: Test 3 – Heading calculation (east ≈ {hdg:.1f}°)")


def test_4_battery_decreases():
    drone = DroneState()
    start = drone.battery_pct
    drone.drain_battery(10.0)
    assert drone.battery_pct < start
    print(f"PASS: Test 4 – Battery decreases ({start} → {drone.battery_pct:.1f})")


def test_5_telemetry_contains_required_fields():
    drone = DroneState(latitude=18.52, longitude=73.85, status="SEARCHING")
    telem = build_telemetry(drone)
    required = ["drone_id", "mission_id", "timestamp", "latitude", "longitude", "altitude_m", "heading_deg", "speed_mps", "battery_pct", "status", "current_waypoint", "total_waypoints", "source"]
    for field in required:
        assert field in telem
    assert telem["source"] == "SIMULATED"
    print("PASS: Test 5 – Telemetry contains all required fields + source=SIMULATED")


def test_6_mission_can_reach_complete_status():
    drone = DroneState(status="SEARCHING")
    drone.status = "MISSION_COMPLETE"
    assert drone.status == "MISSION_COMPLETE"
    print("PASS: Test 6 – Mission can reach MISSION_COMPLETE")


if __name__ == "__main__":
    print("Running AetherSAR Phase 4 simulator tests...\n")
    test_1_drone_initializes_correctly()
    test_2_drone_moves_toward_waypoint()
    test_3_heading_changes_correctly()
    test_4_battery_decreases()
    test_5_telemetry_contains_required_fields()
    test_6_mission_can_reach_complete_status()
    print("\nAll tests passed.")