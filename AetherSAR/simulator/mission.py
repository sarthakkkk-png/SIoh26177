"""
AetherSAR - Simulated mission execution engine.

Deterministic, documented status transitions:

    TAKEOFF -> SEARCHING -> WAYPOINT_REACHED (transient, emitted on arrival)
               -> SEARCHING -> ... -> MISSION_COMPLETE

    SEARCHING -> LOW_BATTERY (emitted once when battery <= BATTERY_CRITICAL)
                 -> RTH (simulated return to the start waypoint)
                 -> STOPPED (home reached, or battery depleted en route)

    any state -> STOPPED (battery depleted or operator interrupt)

`current_waypoint` is the 0-based index of the waypoint the drone is currently
navigating to; it equals the last reached index at the moment of arrival.

The RTH behavior at critical battery is SIMULATED. Nothing here is a real
UAV flight-controller failsafe.
"""

import time
from typing import Callable, Dict, List, Optional

from planner.coordinates import validate_lat_lon
from simulator.drone import DroneState, BATTERY_CRITICAL, DEFAULT_SPEED_MPS
from simulator.path_follower import move_toward_waypoint
from simulator.telemetry import build_telemetry

DT = 0.5
TELEMETRY_INTERVAL = 1.0
SIMULATED_RTH_BATTERY = BATTERY_CRITICAL


def execute_mission(
    drone: DroneState,
    waypoints: List[Dict],
    dt: float = DT,
    telemetry_interval: float = TELEMETRY_INTERVAL,
    tick_delay: Optional[float] = DT,
    on_telemetry: Optional[Callable[[Dict], None]] = None,
) -> DroneState:
    """Fly `drone` through `waypoints`, emitting telemetry via `on_telemetry`.

    - `dt`: simulation seconds advanced per tick.
    - `tick_delay`: wall-clock seconds to sleep per tick (None keeps the
      default pacing; 0.0 runs the mission instantly, used by tests).
    - `on_telemetry`: callback receiving each telemetry record; defaults to
      discarding records (pure computation mode).
    """
    if not waypoints:
        raise ValueError("mission requires at least one waypoint")
    for waypoint in waypoints:
        validate_lat_lon(waypoint["latitude"], waypoint["longitude"])
    if dt <= 0:
        raise ValueError("dt must be positive")
    if telemetry_interval < 0:
        raise ValueError("telemetry_interval must be >= 0")
    if tick_delay is None:
        tick_delay = DT

    emit = on_telemetry if on_telemetry is not None else (lambda _record: None)

    def emit_now() -> None:
        emit(build_telemetry(drone))

    home_lat = float(waypoints[0]["latitude"])
    home_lon = float(waypoints[0]["longitude"])
    drone.total_waypoints = len(waypoints)
    drone.current_waypoint = 0

    emit_now()  # TAKEOFF record

    drone.status = "SEARCHING"
    wp_index = 1
    returning_home = False
    low_battery_emitted = False
    last_telemetry_time = time.monotonic()

    while True:
        # Simulated critical-battery handling: emit LOW_BATTERY once, then RTH.
        if (
            not returning_home
            and not low_battery_emitted
            and drone.battery_pct <= BATTERY_CRITICAL
        ):
            low_battery_emitted = True
            drone.status = "LOW_BATTERY"
            emit_now()
            drone.status = "RTH"
            returning_home = True
            drone.current_waypoint = 0
            emit_now()  # record the simulated RTH transition

        if returning_home:
            target = (home_lat, home_lon)
        elif wp_index < len(waypoints):
            target = (
                float(waypoints[wp_index]["latitude"]),
                float(waypoints[wp_index]["longitude"]),
            )
        else:
            target = None

        if target is None:
            drone.status = "MISSION_COMPLETE"
            drone.current_waypoint = len(waypoints)
            emit_now()
            break

        reached = move_toward_waypoint(drone, target[0], target[1], dt, DEFAULT_SPEED_MPS)
        drone.drain_battery(dt)

        if returning_home:
            if reached:
                drone.status = "STOPPED"
                emit_now()
                break
            drone.status = "RTH"
        elif reached:
            drone.status = "WAYPOINT_REACHED"
            drone.current_waypoint = wp_index
            emit_now()
            wp_index += 1
            if wp_index < len(waypoints):
                drone.status = "SEARCHING"
        else:
            if drone.battery_pct > BATTERY_CRITICAL:
                drone.status = "SEARCHING"
            # else: keep LOW_BATTERY (set by drain_battery); the top-of-loop
            # promotes it to RTH on the next tick, so LOW_BATTERY is never
            # silently overwritten by SEARCHING in emitted telemetry.
            drone.current_waypoint = wp_index

        if time.monotonic() - last_telemetry_time >= telemetry_interval:
            emit_now()
            last_telemetry_time = time.monotonic()

        if drone.battery_pct <= 0 and drone.status != "STOPPED":
            drone.status = "STOPPED"
            emit_now()
            break

        if tick_delay > 0:
            time.sleep(tick_delay)

    return drone