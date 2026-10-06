"""Build the Bengaluru case-study instance from raw inputs (run fetch_data.py first).

    uv run python scripts/build_instance.py

Outputs (data/processed/):
  blr_demand_cells.csv   ~500 m population cells inside BBMP (demand nodes)
  blr_candidates.csv     OSM grocery/convenience/warehouse sites, de-duplicated within ~165 m
  blr_wards.csv          ward id/name/area (for maps and ward-level reporting)
  detour_calibration.json  road/straight-line ratio from an OSRM sample
"""

import json

import numpy as np
import pandas as pd

from orpaper.config import ROOT, load_config
from orpaper.data.geo import city_boundary, dedupe_sites, osm_sites, population_grid, read_wards_kml
from orpaper.data.osrm import haversine_matrix, osrm_matrix

RAW = ROOT / "data/raw"
OUT = ROOT / "data/processed"
POP = RAW / "worldpop/blr_pop_2025_100m_R2025A.tif"


def calibrate_detour(cells: pd.DataFrame, n=40, seed=0) -> dict:
    """Median OSRM road distance / haversine distance over a random sample of cell pairs.

    The public OSRM demo uses a car profile; two-wheelers in Bengaluru follow
    similar streets, so the ratio (not the car speed) is what we reuse.
    """
    cache = OUT / "osrm_sample.json"
    sample = cells.sample(n=min(n, len(cells)), random_state=seed)
    latlon = sample[["lat", "lon"]].to_numpy()
    road_km, road_min = osrm_matrix(latlon, cache=cache)
    straight = haversine_matrix(latlon)
    mask = (straight > 0.5) & (straight < 6)  # dark-store-relevant range
    ratio = road_km[mask] / straight[mask]
    car_speed = road_km[mask] / (road_min[mask] / 60)
    return {"pairs": int(mask.sum()), "detour_median": float(np.median(ratio)),
            "detour_p25": float(np.percentile(ratio, 25)), "detour_p75": float(np.percentile(ratio, 75)),
            "osrm_car_speed_kmh_median": float(np.median(car_speed)),
            "note": "OSRM demo (car profile, free-flow). Only the detour ratio is used."}


def main():
    cfg = load_config()
    block = cfg["case"]["grid_block"]
    OUT.mkdir(parents=True, exist_ok=True)

    wards = read_wards_kml(RAW / "bbmp/bbmp_wards_2022.kml")
    boundary = city_boundary(wards)
    wards.assign(area_km2=wards["geometry"].map(lambda g: g.area * 111.32 ** 2 * np.cos(np.radians(12.97))))\
        .drop(columns="geometry").to_csv(OUT / "blr_wards.csv", index=False)

    cells = population_grid(POP, boundary, block=block)
    control = cfg["case"]["population_control_total"]
    cells["pop_worldpop"] = cells["pop"]
    cells["pop"] = cells["pop_worldpop"] * control / cells["pop_worldpop"].sum()
    cells.to_csv(OUT / "blr_demand_cells.csv", index=False)

    sites = osm_sites(RAW / "osm/candidate_sites.json", boundary)
    sites.to_csv(OUT / "blr_osm_sites.csv", index=False)
    cand = dedupe_sites(sites)
    cand.to_csv(OUT / "blr_candidates.csv", index=False)

    detour = calibrate_detour(cells)
    (OUT / "detour_calibration.json").write_text(json.dumps(detour, indent=2))

    summary = {
        "wards": len(wards),
        "bbmp_area_km2": round(float(boundary.area * 111.32 ** 2 * np.cos(np.radians(12.97))), 1),
        "grid_block_100m": block,
        "demand_cells": len(cells),
        "population_worldpop_in_bbmp": round(float(cells["pop_worldpop"].sum())),
        "population_scaled_to": control,
        "scale_factor": round(control / float(cells["pop_worldpop"].sum()), 4),
        "osm_sites_in_bbmp": len(sites),
        "osm_sites_by_kind": sites["kind"].value_counts().to_dict(),
        "candidate_sites": len(cand),
        "detour": detour,
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/instance_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
