"""
AetherSAR - Geographic search-area abstraction.

A search area is represented as an axis-aligned geographic bounding box in
WGS84 coordinates. Metric sizes use a simple equirectangular approximation
(1 degree of latitude = 111,320 m; degrees of longitude scaled by
cos(latitude)), which is accurate to well under 1% for the small areas used
by this simulated prototype.
"""

import math
from dataclasses import dataclass

from planner.coordinates import validate_latitude, validate_longitude

M_PER_DEG_LAT = 111_320.0


def meters_per_degree_lon(latitude: float) -> float:
    """Approximate metres per degree of longitude at the given latitude."""
    return M_PER_DEG_LAT * math.cos(math.radians(latitude))


@dataclass(frozen=True)
class SearchArea:
    """A rectangular geographic search area (WGS84 bounding box)."""

    min_lat: float
    min_lon: float
    max_lat: float
    max_lon: float

    def __post_init__(self) -> None:
        min_lat = validate_latitude(self.min_lat)
        min_lon = validate_longitude(self.min_lon)
        max_lat = validate_latitude(self.max_lat)
        max_lon = validate_longitude(self.max_lon)
        if min_lat >= max_lat:
            raise ValueError(f"min_lat ({min_lat}) must be less than max_lat ({max_lat})")
        if min_lon >= max_lon:
            raise ValueError(f"min_lon ({min_lon}) must be less than max_lon ({max_lon})")
        object.__setattr__(self, "min_lat", min_lat)
        object.__setattr__(self, "min_lon", min_lon)
        object.__setattr__(self, "max_lat", max_lat)
        object.__setattr__(self, "max_lon", max_lon)

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2.0

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2.0

    @property
    def height_m(self) -> float:
        """Approximate area height in metres (equirectangular)."""
        return (self.max_lat - self.min_lat) * M_PER_DEG_LAT

    @property
    def width_m(self) -> float:
        """Approximate area width in metres (equirectangular)."""
        return (self.max_lon - self.min_lon) * meters_per_degree_lon(self.center_lat)

    def contains(self, latitude: float, longitude: float) -> bool:
        """True if the given WGS84 coordinate lies inside the bounding box."""
        return (
            self.min_lat <= latitude <= self.max_lat
            and self.min_lon <= longitude <= self.max_lon
        )

    def to_dict(self) -> dict:
        return {
            "min_lat": self.min_lat,
            "min_lon": self.min_lon,
            "max_lat": self.max_lat,
            "max_lon": self.max_lon,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SearchArea":
        try:
            return cls(
                min_lat=data["min_lat"],
                min_lon=data["min_lon"],
                max_lat=data["max_lat"],
                max_lon=data["max_lon"],
            )
        except KeyError as exc:
            raise ValueError(f"search area missing required key: {exc.args[0]}") from exc