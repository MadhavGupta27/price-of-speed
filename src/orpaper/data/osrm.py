"""Real road distance/duration matrices from OSRM, with a haversine fallback.

The public demo server (router.project-osrm.org) is rate-limited and meant for
light use: fetch once, cache to data/processed/, and cite it in data/README.md.
Coordinates are (lat, lon); OSRM expects lon,lat in the URL.
"""

import json
from pathlib import Path

import numpy as np
import requests

OSRM_URL = "https://router.project-osrm.org/table/v1/driving/"
EARTH_RADIUS_KM = 6371.0088


def haversine_matrix(latlon):
    """Great-circle distance matrix in km."""
    p = np.radians(np.asarray(latlon, float))
    lat, lon = p[:, 0][:, None], p[:, 1][:, None]
    dlat, dlon = lat - lat.T, lon - lon.T
    a = np.sin(dlat / 2) ** 2 + np.cos(lat) * np.cos(lat.T) * np.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.sqrt(a))


def osrm_matrix(latlon, cache: Path | None = None, base_url=OSRM_URL, timeout=60):
    """Return (distance_km, duration_min) road matrices. Cached as JSON if `cache` given."""
    if cache and Path(cache).exists():
        d = json.loads(Path(cache).read_text())
        return np.array(d["distance_km"]), np.array(d["duration_min"])

    coords = ";".join(f"{lon},{lat}" for lat, lon in latlon)
    r = requests.get(base_url + coords, params={"annotations": "distance,duration"},
                     timeout=timeout)
    r.raise_for_status()
    body = r.json()
    if body.get("code") != "Ok":
        raise RuntimeError(f"OSRM error: {body.get('code')} {body.get('message')}")
    dist = np.array(body["distances"], float) / 1000.0
    dur = np.array(body["durations"], float) / 60.0

    if cache:
        Path(cache).parent.mkdir(parents=True, exist_ok=True)
        Path(cache).write_text(json.dumps({"latlon": [list(map(float, p)) for p in latlon],
                                           "distance_km": dist.tolist(),
                                           "duration_min": dur.tolist()}))
    return dist, dur
