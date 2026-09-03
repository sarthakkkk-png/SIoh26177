"""
AetherSAR - WGS84 coordinate validation.

Standard library only. Rejects NaN/infinity values and out-of-range
latitudes and longitudes instead of silently converting them.
"""

import math

MIN_LATITUDE = -90.0
MAX_LATITUDE = 90.0
MIN_LONGITUDE = -180.0
MAX_LONGITUDE = 180.0


def _finite_float(value, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got boolean {value!r}")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return result


def validate_latitude(value) -> float:
    """Validate a latitude; returns it as a float."""
    latitude = _finite_float(value, "latitude")
    if not (MIN_LATITUDE <= latitude <= MAX_LATITUDE):
        raise ValueError(f"latitude {latitude} out of range [{MIN_LATITUDE}, {MAX_LATITUDE}]")
    return latitude


def validate_longitude(value) -> float:
    """Validate a longitude; returns it as a float."""
    longitude = _finite_float(value, "longitude")
    if not (MIN_LONGITUDE <= longitude <= MAX_LONGITUDE):
        raise ValueError(f"longitude {longitude} out of range [{MIN_LONGITUDE}, {MAX_LONGITUDE}]")
    return longitude


def validate_lat_lon(latitude, longitude):
    """Validate a coordinate pair and return (latitude, longitude) as floats."""
    return validate_latitude(latitude), validate_longitude(longitude)