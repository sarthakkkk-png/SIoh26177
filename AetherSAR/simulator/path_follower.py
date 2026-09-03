"""
AetherSAR Phase 4 – Simple Waypoint Follower
"""

import math
from typing import List, Dict
from simulator.drone import DroneState, WAYPOINT_REACH_THRESHOLD_M, DEFAULT_SPEED_MPS


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    x = math.sin(dlambda) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def move_toward_waypoint(drone: DroneState, target_lat: float, target_lon: float, dt_seconds: float, speed_mps: float = DEFAULT_SPEED_MPS) -> bool:
    dist = haversine_distance_m(drone.latitude, drone.longitude, target_lat, target_lon)

    if dist <= WAYPOINT_REACH_THRESHOLD_M:
        drone.latitude = target_lat
        drone.longitude = target_lon
        return True

    step = min(speed_mps * dt_seconds, dist)
    ratio = step / dist

    drone.latitude += (target_lat - drone.latitude) * ratio
    drone.longitude += (target_lon - drone.longitude) * ratio
    drone.heading_deg = calculate_heading(drone.latitude, drone.longitude, target_lat, target_lon)
    drone.speed_mps = speed_mps
    return False