"""
AetherSAR - Lawnmower (boustrophedon) search-path planner.

Generates an ordered, deterministic waypoint list that covers a rectangular
search area with parallel tracks of alternating direction. Tracks are spaced
no more than `spacing_m` apart, and interior waypoints along a track are also
spaced no more than `spacing_m` apart. All generated coordinates stay inside
the requested bounding box and no two consecutive waypoints are identical.

Geographic approximation: 1 degree of latitude = 111,320 m, and degrees of
longitude are scaled by cos(latitude) (equirectangular projection). Suitable
for the small search areas used by this simulated prototype; it is not
production-grade GIS.
"""

import math
from typing import List

from planner.coordinates import validate_latitude, validate_longitude
from planner.search_area import SearchArea, M_PER_DEG_LAT, meters_per_degree_lon


def generate_lawnmower(search_area: SearchArea, spacing_m: float) -> List[dict]:
    """Generate ordered lawnmower waypoints for a search area.

    Returns a list of dicts in the canonical waypoint structure:
        {"latitude": float, "longitude": float}
    """
    if not isinstance(search_area, SearchArea):
        raise TypeError("search_area must be a SearchArea")
    if isinstance(spacing_m, bool):
        raise ValueError(f"spacing_m must be a positive finite number, got {spacing_m!r}")
    try:
        spacing = float(spacing_m)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"spacing_m must be a number, got {spacing_m!r}") from exc
    if not math.isfinite(spacing) or spacing <= 0:
        raise ValueError(f"spacing_m must be a positive finite number, got {spacing_m!r}")

    # Track count: number of spacing intervals across each dimension,
    # clamped to at least one so tiny areas still produce a valid path.
    lat_intervals = max(1, math.ceil(search_area.height_m / spacing))
    lon_intervals = max(1, math.ceil(search_area.width_m / spacing))

    lat_step = (search_area.max_lat - search_area.min_lat) / lat_intervals
    lon_step = (search_area.max_lon - search_area.min_lon) / lon_intervals

    raw_points = []  # list of (lat, lon)
    for track_index in range(lat_intervals + 1):
        lat = search_area.min_lat + track_index * lat_step
        eastward = track_index % 2 == 0
        start_lon = search_area.min_lon if eastward else search_area.max_lon
        end_lon = search_area.max_lon if eastward else search_area.min_lon
        for point_index in range(lon_intervals + 1):
            lon = start_lon + (end_lon - start_lon) * (point_index / lon_intervals)
            raw_points.append((lat, lon))

    waypoints: List[dict] = []
    for lat, lon in raw_points:
        # Validate, round for clean output, and clamp so rounding can never
        # push a generated coordinate outside the requested bounding box.
        lat = min(max(round(validate_latitude(lat), 6), search_area.min_lat), search_area.max_lat)
        lon = min(max(round(validate_longitude(lon), 6), search_area.min_lon), search_area.max_lon)
        waypoint = {"latitude": lat, "longitude": lon}
        if waypoints and waypoints[-1] == waypoint:
            continue  # defensive: never emit consecutive duplicates
        waypoints.append(waypoint)

    return waypoints