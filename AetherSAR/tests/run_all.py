"""Run every AetherSAR test module from the repository root:

    python3 -m tests.run_all
"""

import subprocess
import sys
from pathlib import Path

TEST_MODULES = [
    "simulator.tests.test_simulator",
    "tests.test_coordinates",
    "tests.test_search_area",
    "tests.test_search_planner",
    "tests.test_waypoints",
    "tests.test_detection",
    "tests.test_mission",
]


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    failures = 0
    for module in TEST_MODULES:
        print(f"\n=== {module} ===")
        result = subprocess.run([sys.executable, "-m", module], cwd=root)
        if result.returncode != 0:
            failures += 1
    print("\n" + "=" * 48)
    if failures:
        print(f"{failures} test module(s) FAILED")
        return 1
    print("ALL TEST MODULES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())