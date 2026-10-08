# Data licences

## OpenStreetMap-derived data (ODbL 1.0)

These files are Derivative Databases of OpenStreetMap:

- `raw/osm/candidate_sites.json`
- `processed/blr_osm_sites.csv`
- `processed/blr_candidates.csv`
- `processed/osrm_sample.json`
- `processed/detour_calibration.json`

They contain information from OpenStreetMap, which is made available under the
Open Database License (ODbL 1.0); see [`../licenses/ODbL-1.0.txt`](../licenses/ODbL-1.0.txt).
In accordance with ODbL section 4.4 (share-alike), these files are themselves
offered under ODbL 1.0.

> © OpenStreetMap contributors. https://www.openstreetmap.org/copyright

## WorldPop-derived data (CC BY 4.0)

`raw/worldpop/blr_pop_2025_100m_R2025A.tif` (clipped) and
`processed/blr_demand_cells.csv` (aggregated and rescaled) are derived from
WorldPop Global2 R2025A, India 2025, 100 m constrained population counts
(University of Southampton), licensed CC BY 4.0. Changes: clipped to the
Bengaluru bounding box, aggregated to 5×5 cells, scaled to the Census 2011 total.

## BBMP ward boundaries

`raw/bbmp/bbmp_wards_2022.kml` and `processed/blr_wards.csv`: OpenCity.in,
BBMP Ward Map 2022 (credit: Devdatta Tengshe), listed as public domain.

## Other processed files

`processed/order_hour_profile.csv` is derived from a Kaggle dataset (licence
"other") and is illustrative only; the raw Kaggle files are not redistributed.

Provenance, hashes and access dates for every source: `raw/MANIFEST.json`.
