"""Spatial preprocessing for the Bengaluru case: ward boundaries, population grid, candidate sites."""

import json
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from shapely import contains_xy
from shapely.geometry import Polygon
from shapely.ops import unary_union

KML_NS = {"k": "http://www.opengis.net/kml/2.2"}


def _ring(text: str):
    pts = [tuple(map(float, c.split(",")[:2])) for c in text.split()]
    return pts  # (lon, lat)


def read_wards_kml(path) -> pd.DataFrame:
    """One row per ward: attributes + shapely polygon (lon/lat)."""
    root = ET.parse(path).getroot()
    rows = []
    for pm in root.iterfind(".//k:Placemark", KML_NS):
        attrs = {sd.get("name"): sd.text for sd in pm.iterfind(".//k:SimpleData", KML_NS)}
        polys = []
        for poly in pm.iterfind(".//k:Polygon", KML_NS):
            outer = poly.find("k:outerBoundaryIs//k:coordinates", KML_NS)
            holes = [_ring(h.text) for h in poly.iterfind("k:innerBoundaryIs//k:coordinates", KML_NS)]
            polys.append(Polygon(_ring(outer.text), holes))
        attrs["geometry"] = unary_union(polys).buffer(0)
        rows.append(attrs)
    return pd.DataFrame(rows)


def city_boundary(wards: pd.DataFrame):
    return unary_union(list(wards["geometry"])).buffer(0)


def population_grid(raster_path, boundary, block: int = 5) -> pd.DataFrame:
    """Aggregate a population raster into block x block super-cells inside `boundary`.

    Returns cell id, centroid lat/lon and population. Cells whose centroid lies
    outside the boundary or with zero population are dropped.
    """
    import rasterio

    with rasterio.open(raster_path) as src:
        a = src.read(1).astype(float)
        a[a == src.nodata] = 0
        a[a < 0] = 0
        t = src.transform
    H, W = (a.shape[0] // block) * block, (a.shape[1] // block) * block
    agg = a[:H, :W].reshape(H // block, block, W // block, block).sum(axis=(1, 3))
    rows, cols = np.nonzero(agg > 0)
    # centroid of super-cell in raster coordinates -> lon/lat
    cx = t.c + (cols * block + block / 2) * t.a
    cy = t.f + (rows * block + block / 2) * t.e
    inside = contains_xy(boundary, cx, cy)
    df = pd.DataFrame({"row": rows, "col": cols, "lon": cx, "lat": cy, "pop": agg[rows, cols]})[inside]
    df.insert(0, "cell_id", [f"r{r}c{c}" for r, c in zip(df["row"], df["col"])])
    return df.reset_index(drop=True)


def osm_sites(overpass_json_path, boundary) -> pd.DataFrame:
    """Flatten Overpass elements (nodes and way/relation centres) inside the boundary."""
    els = json.loads(open(overpass_json_path).read())["elements"]
    rows = []
    for e in els:
        lat = e.get("lat", e.get("center", {}).get("lat"))
        lon = e.get("lon", e.get("center", {}).get("lon"))
        if lat is None:
            continue
        tags = e.get("tags", {})
        kind = tags.get("shop") or ("warehouse" if tags.get("building") == "warehouse" else "other")
        rows.append({"osm_id": f"{e['type']}/{e['id']}", "lat": lat, "lon": lon, "kind": kind,
                     "name": tags.get("name", "")})
    df = pd.DataFrame(rows)
    return df[contains_xy(boundary, df["lon"], df["lat"])].reset_index(drop=True)


def dedupe_sites(points: pd.DataFrame, cell_deg: float = 0.0015) -> pd.DataFrame:
    """One candidate per ~cell_deg square (0.0015 deg ~ 165 m): mean position, site count kept.

    Candidates keep (near-)true coordinates; snapping them to the demand grid
    would make all distances lattice multiples and hide radius changes.
    """
    key = (np.floor(points["lat"] / cell_deg).astype(int).astype(str) + "_"
           + np.floor(points["lon"] / cell_deg).astype(int).astype(str))
    g = points.assign(key=key).groupby("key")
    out = g.agg(lat=("lat", "mean"), lon=("lon", "mean"), osm_sites=("osm_id", "size"),
                kinds=("kind", lambda k: ";".join(sorted(set(k))))).reset_index(drop=True)
    out.insert(0, "site_id", [f"s{i}" for i in range(len(out))])
    return out
