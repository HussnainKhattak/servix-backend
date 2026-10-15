import math
from typing import Optional


def calculate_haversine_distance(
    lat1: float, lon1: float, lat2: float, lon2: float
) -> float:
    """
    Calculate the great-circle distance between two points on the Earth (in miles).
    Formula: Haversine
    """
    earth_radius_miles = 3958.8

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(earth_radius_miles * c, 1)


def is_within_radius(
    job_lat: Optional[float],
    job_lon: Optional[float],
    provider_lat: Optional[float],
    provider_lon: Optional[float],
    radius_miles: float,
) -> bool:
    """Check whether a job is within a service provider's operational radius."""
    if not all([job_lat, job_lon, provider_lat, provider_lon]):
        return True  # Fallback to true if coordinates are missing

    distance = calculate_haversine_distance(
        job_lat, job_lon, provider_lat, provider_lon
    )
    return distance <= radius_miles
