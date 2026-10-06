"""Download every raw case-study input and record provenance in data/raw/MANIFEST.json.

    uv run python scripts/fetch_data.py            # all sources
    uv run python scripts/fetch_data.py --only osm # one source

Each source writes into its own directory under data/raw/. The manifest records
URL, access timestamp, SHA-256 and licence so data/README.md and the paper's
Data section can cite exact inputs. Re-running skips files already present.

Large inputs (WorldPop India raster, ~780 MB) are clipped to the study area and
the national file deleted, so only the Bengaluru clip is kept (see .gitignore).
"""

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests

from orpaper.config import ROOT

RAW = ROOT / "data/raw"
MANIFEST = RAW / "MANIFEST.json"

# Study area: Bengaluru (BBMP). Bounding box generously covers the 2022 ward map.
BBOX = {"west": 77.40, "south": 12.80, "east": 77.85, "north": 13.15}

WORLDPOP_URL = ("https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/2025/IND/v1/"
                "100m/constrained/ind_pop_2025_CN_100m_R2025A_v1.tif")
BBMP_WARDS_URL = ("https://data.opencity.in/dataset/87b978d1-352e-4b90-aa2c-9991e55d3425/resource/"
                  "9423dbca-db2b-47df-823e-8546f4fb8f2a/download/53418b48-c08d-43bd-be0e-31b46cd0f798.kml")
GEOFABRIK_LATEST = "https://download.geofabrik.de/asia/india/southern-zone-latest.osm.pbf"

KAGGLE = {
    "gauravmalik26/food-delivery-dataset": "kaggle_gauravmalik26_food-delivery-dataset",
    "saurabhbadole/zomato-delivery-operations-analytics-dataset":
        "kaggle_saurabhbadole_zomato-delivery-operations-analytics-dataset",
    "akxiit/blinkit-sales-dataset": "kaggle_akxiit_blinkit-sales-dataset",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}


def record(manifest: dict, key: str, **entry):
    """Keep the original access time if the content (hashes) is unchanged."""
    prev = manifest.get(key, {})
    same = {k: prev.get(k) for k in ("sha256", "files")} == {k: entry.get(k) for k in ("sha256", "files")}
    manifest[key] = {"accessed_utc": prev["accessed_utc"] if prev and same else now(), **entry}
    MANIFEST.write_text(json.dumps(manifest, indent=2))


def download(url: str, dest: Path, timeout=120):
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    tmp.rename(dest)


def fetch_worldpop(m):
    import rasterio
    from rasterio.windows import from_bounds

    out_dir = RAW / "worldpop"
    clip = out_dir / "blr_pop_2025_100m_R2025A.tif"
    if clip.exists():
        print("worldpop: clip exists, skipping")
        return
    national = out_dir / "ind_pop_2025_CN_100m_R2025A_v1.tif"
    if not national.exists():
        print("worldpop: downloading national raster (~780 MB)...")
        download(WORLDPOP_URL, national, timeout=600)
    national_sha = sha256(national)
    with rasterio.open(national) as src:
        w = from_bounds(BBOX["west"], BBOX["south"], BBOX["east"], BBOX["north"], src.transform)
        data = src.read(1, window=w)
        prof = src.profile | {"height": data.shape[0], "width": data.shape[1],
                              "transform": src.window_transform(w), "compress": "deflate"}
    with rasterio.open(clip, "w", **prof) as dst:
        dst.write(data, 1)
    national.unlink()  # keep only the study-area clip
    record(m, "worldpop", url=WORLDPOP_URL, file=str(clip.relative_to(ROOT)),
           sha256=sha256(clip), source_sha256_national=national_sha, bbox=BBOX,
           licence="CC BY 4.0",
           citation="WorldPop (2025). Global2 R2025A constrained population, India 2025, 100 m. "
                    "University of Southampton. (Confirm DOI on hub.worldpop.org before citing.)",
           note="National raster clipped to BBOX then deleted.")
    print(f"worldpop: wrote {clip}")


def fetch_bbmp(m):
    dest = RAW / "bbmp" / "bbmp_wards_2022.kml"
    if not dest.exists():
        download(BBMP_WARDS_URL, dest)
    record(m, "bbmp_wards_2022", url=BBMP_WARDS_URL, file=str(dest.relative_to(ROOT)),
           sha256=sha256(dest), licence="Public Domain (OpenCity.in listing)",
           citation="OpenCity (2022). BBMP Ward Map - 2022 (243 wards). Credit: Devdatta Tengshe.")
    print(f"bbmp: {dest}")


SITE_SHOPS = {"supermarket", "convenience", "grocery", "greengrocer"}


def _site(o):
    """Return kind if the OSM object is a candidate dark-store site, else None."""
    shop = o.tags.get("shop")
    if shop in SITE_SHOPS:
        return shop
    if o.tags.get("building") == "warehouse":
        return "warehouse"
    return None


def fetch_osm(m):
    """Candidate sites from a dated Geofabrik extract (reproducible snapshot).

    The live Overpass API was tried first but its public instances were
    unavailable (504/timeouts) on 2026-10-06; a dated extract is also easier
    to cite. The ~560 MB extract is filtered to BBOX and then deleted.
    """
    import osmium

    out_dir = RAW / "osm"
    dest = out_dir / "candidate_sites.json"
    if dest.exists():
        print("osm: sites exist, skipping")
        return
    out_dir.mkdir(parents=True, exist_ok=True)
    r = requests.head(GEOFABRIK_LATEST, allow_redirects=False, timeout=60)
    dated_url = r.headers.get("Location", GEOFABRIK_LATEST)
    pbf = out_dir / dated_url.rsplit("/", 1)[1]
    if not pbf.exists():
        print(f"osm: downloading {dated_url} (~560 MB)...")
        download(dated_url, pbf, timeout=900)
    md5_expected = requests.get(dated_url + ".md5", timeout=60).text.split()[0]
    md5 = hashlib.md5(pbf.read_bytes()).hexdigest()
    if md5 != md5_expected:
        raise RuntimeError(f"md5 mismatch for {pbf.name}: {md5} != {md5_expected}")

    def in_bbox(lat, lon):
        return BBOX["south"] <= lat <= BBOX["north"] and BBOX["west"] <= lon <= BBOX["east"]

    elements = []
    fp = (osmium.FileProcessor(str(pbf)).with_locations()
          .with_filter(osmium.filter.KeyFilter("shop", "building")))
    for o in fp:
        kind = _site(o)
        if kind is None:
            continue
        if o.is_node():
            lat, lon = o.location.lat, o.location.lon
            typ = "node"
        elif o.is_way():
            pts = [(n.location.lat, n.location.lon) for n in o.nodes if n.location.valid()]
            if not pts:
                continue
            lat, lon = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
            typ = "way"
        else:
            continue
        if in_bbox(lat, lon):
            elements.append({"type": typ, "id": o.id, "lat": lat, "lon": lon,
                             "tags": {k: o.tags.get(k) for k in ("shop", "building", "name")
                                      if o.tags.get(k)}})
    dest.write_text(json.dumps({"source": dated_url, "elements": elements}))
    pbf.unlink()
    record(m, "osm_candidate_sites", url=dated_url, source_md5=md5, file=str(dest.relative_to(ROOT)),
           sha256=sha256(dest), elements=len(elements), bbox=BBOX,
           filter="shop in {supermarket, convenience, grocery, greengrocer} or building=warehouse; "
                  "ways reduced to node-mean centroid",
           licence="ODbL 1.0 (© OpenStreetMap contributors)",
           citation=f"OpenStreetMap contributors, Geofabrik extract {pbf.name}")
    print(f"osm: {len(elements)} sites -> {dest}")


def fetch_kaggle(m):
    for ref, folder in KAGGLE.items():
        d = RAW / folder
        if not any(d.glob("*.csv")):
            subprocess.run(["kaggle", "datasets", "download", ref, "-p", str(d), "--unzip"], check=True)
            subprocess.run(["kaggle", "datasets", "metadata", ref, "-p", str(d)], check=True)
        meta = json.loads((d / "dataset-metadata.json").read_text())
        meta = json.loads(meta) if isinstance(meta, str) else meta
        files = {p.name: sha256(p) for p in sorted(d.glob("*.csv"))}
        record(m, f"kaggle:{ref}", url=f"https://www.kaggle.com/datasets/{ref}",
               folder=str(d.relative_to(ROOT)), files=files,
               licence=str(meta.get("licenses")), title=meta.get("title"))
        print(f"kaggle: {ref} ({len(files)} csv)")


SOURCES = {"worldpop": fetch_worldpop, "bbmp": fetch_bbmp, "osm": fetch_osm, "kaggle": fetch_kaggle}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=SOURCES)
    a = ap.parse_args()
    m = load_manifest()
    for name, fn in SOURCES.items():
        if a.only in (None, name):
            fn(m)


if __name__ == "__main__":
    main()
