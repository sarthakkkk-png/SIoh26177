"""
AetherSAR - Simulated drone mission runner (CLI).

SOFTWARE SIMULATION ONLY. Does not control any physical UAV.

Primary demo path: search area -> generated lawnmower waypoints -> mission.
Legacy path: --waypoints <file> runs a manually authored waypoint file.

Run from the repository root:

    python3 -m simulator.main                                  # generated search path (default area)
    python3 -m simulator.main --area 18.5204 73.8567 18.5228 73.8599 --spacing 85
    python3 -m simulator.main --waypoints simulator/waypoints.json
    python3 -m simulator.main --no-delay                       # run instantly (fast verification)
"""

import argparse
import sys
from pathlib import Path
from typing import Dict, List, Optional

if __package__ in (None, ""):
    # Running as a plain script (python3 simulator/main.py) instead of as a
    # module (python3 -m simulator.main): make the project root importable
    # so the package imports below resolve from anywhere.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from planner.search_area import SearchArea
from planner.search_planner import generate_lawnmower
from simulator.drone import (
    DroneState,
    DRONE_ID,
    MISSION_ID,
    DEFAULT_ALTITUDE_M,
    DEFAULT_SPEED_MPS,
    INITIAL_BATTERY,
)
from simulator.mission import execute_mission
from simulator.telemetry import (
    build_telemetry,
    print_telemetry,
    save_telemetry,
    clear_telemetry_file,
)
from simulator.waypoints import load_waypoints

DEFAULT_SEARCH_AREA = SearchArea(
    min_lat=18.5204,
    min_lon=73.8567,
    max_lat=18.5228,
    max_lon=73.8599,
)
DEFAULT_SPACING_M = 85.0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AetherSAR simulated drone mission runner")
    source = parser.add_mutually_exclusive_group()
    source.add_argument(
        "--waypoints",
        type=Path,
        metavar="FILE",
        help="run a manually authored waypoint file (legacy)",
    )
    source.add_argument(
        "--area",
        nargs=4,
        type=float,
        metavar=("MIN_LAT", "MIN_LON", "MAX_LAT", "MAX_LON"),
        help="search-area bounding box (generates a lawnmower path)",
    )
    parser.add_argument(
        "--spacing",
        type=float,
        default=DEFAULT_SPACING_M,
        metavar="METERS",
        help="lawnmower track spacing in metres (default: %(default)s)",
    )
    parser.add_argument(
        "--no-delay",
        action="store_true",
        help="run without wall-clock pacing (fast verification)",
    )
    return parser


def make_drone(start_lat: float, start_lon: float, total_waypoints: int) -> DroneState:
    return DroneState(
        latitude=float(start_lat),
        longitude=float(start_lon),
        altitude_m=DEFAULT_ALTITUDE_M,
        speed_mps=DEFAULT_SPEED_MPS,
        battery_pct=INITIAL_BATTERY,
        status="TAKEOFF",
        current_waypoint=0,
        total_waypoints=total_waypoints,
    )


def run_mission_demo(waypoints: List[Dict], description: str, tick_delay: Optional[float]) -> DroneState:
    print("=" * 64)
    print("AetherSAR - Simulated Drone Mission")
    print("SOFTWARE SIMULATION ONLY - all flight data is SIMULATED")
    print("=" * 64)
    print(f"Path source: {description} ({len(waypoints)} waypoints)")
    print(f"Drone {DRONE_ID} | Mission {MISSION_ID} | Altitude {DEFAULT_ALTITUDE_M} m (SIMULATED)")
    print("-" * 64)

    clear_telemetry_file()

    def on_telemetry(telem: Dict) -> None:
        print_telemetry(telem)
        save_telemetry(telem)

    drone = make_drone(waypoints[0]["latitude"], waypoints[0]["longitude"], len(waypoints))
    try:
        drone = execute_mission(drone, waypoints, tick_delay=tick_delay, on_telemetry=on_telemetry)
    except KeyboardInterrupt:
        drone.status = "STOPPED"
        on_telemetry(build_telemetry(drone))
        print("\n[SIM] Mission interrupted by user")

    print("-" * 64)
    print(f"Mission finished with status: {drone.status}")
    print(f"Telemetry saved to: {Path('simulator/output/telemetry.jsonl')}")
    print("All telemetry records contain source=SIMULATED")
    return drone


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    tick_delay = 0.0 if args.no_delay else None

    try:
        if args.waypoints is not None:
            waypoints = load_waypoints(args.waypoints)
            description = f"manual waypoint file {args.waypoints.name}"
        else:
            area = SearchArea(*args.area) if args.area is not None else DEFAULT_SEARCH_AREA
            waypoints = generate_lawnmower(area, args.spacing)
            description = (
                f"generated lawnmower search path over bbox "
                f"({area.min_lat}, {area.min_lon}) - ({area.max_lat}, {area.max_lon}), "
                f"spacing {args.spacing} m"
            )
    except (ValueError, FileNotFoundError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    run_mission_demo(waypoints, description, tick_delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())