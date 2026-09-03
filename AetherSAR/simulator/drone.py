"""
AetherSAR Phase 4 – Simulated Drone State
Software simulation only. Does not control any physical UAV.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import math


# -------------------- Configuration --------------------
DRONE_ID = "DRONE-01"
MISSION_ID = "MISSION-001"
DEFAULT_ALTITUDE_M = 80.0
DEFAULT_SPEED_MPS = 8.0
INITIAL_BATTERY = 100.0
BATTERY_DRAIN_PER_SECOND = 0.08
BATTERY_WARNING = 30.0
BATTERY_CRITICAL = 15.0
WAYPOINT_REACH_THRESHOLD_M = 12.0


@dataclass
class DroneState:
    drone_id: str = DRONE_ID
    mission_id: str = MISSION_ID
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_m: float = DEFAULT_ALTITUDE_M
    heading_deg: float = 0.0
    speed_mps: float = DEFAULT_SPEED_MPS
    battery_pct: float = INITIAL_BATTERY
    status: str = "IDLE"
    current_waypoint: int = 0
    total_waypoints: int = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))
    source: str = "SIMULATED"

    def update_timestamp(self) -> None:
        self.timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    def drain_battery(self, dt_seconds: float) -> None:
        self.battery_pct = max(0.0, self.battery_pct - BATTERY_DRAIN_PER_SECOND * dt_seconds)
        if self.battery_pct <= BATTERY_CRITICAL and self.status not in ("MISSION_COMPLETE", "STOPPED"):
            self.status = "LOW_BATTERY"

    def to_dict(self) -> dict:
        return {
            "drone_id": self.drone_id,
            "mission_id": self.mission_id,
            "timestamp": self.timestamp,
            "latitude": round(self.latitude, 6),
            "longitude": round(self.longitude, 6),
            "altitude_m": round(self.altitude_m, 1),
            "heading_deg": round(self.heading_deg, 1),
            "speed_mps": round(self.speed_mps, 1),
            "battery_pct": round(self.battery_pct, 1),
            "status": self.status,
            "current_waypoint": self.current_waypoint,
            "total_waypoints": self.total_waypoints,
            "source": self.source,
        }