# Case-study data: Bengaluru quick-commerce instance

The data for the paper's Data section and reproducibility claims. Everything here regenerates with:

```bash
make data        # = scripts/fetch_data.py + scripts/audit_kaggle.py + scripts/build_instance.py
```

Exact URLs, access times, hashes and licences are in [`raw/MANIFEST.json`](raw/MANIFEST.json), which `fetch_data.py` writes. Nothing in `raw/` is edited by hand.

## 1. Acquisition procedure (as executed, 2026-10-06)

| # | Step | Tool | Outcome |
|---|---|---|---|
| 1 | Searched the resources named in the guidelines (Kaggle, UCI, OSM/OSRM, government portals) for Indian last-mile data | web search, `kaggle datasets list` | Candidates: Kaggle *Food Delivery Dataset* (gauravmalik26), *Zomato Delivery Operations Analytics* (saurabhbadole, a re-upload of the same data), *Blinkit Sales Dataset* (akxiit) |
| 2 | Downloaded the three Kaggle datasets with metadata | `kaggle` CLI | 45,593 + 45,584 delivery rows; 9 Blinkit tables |
| 3 | **Audited them before use** | `scripts/audit_kaggle.py` → `results/data_audit_kaggle.json` | **Rejected as geography sources** (see §3) |
| 4 | Study area: BBMP 2022 ward map (243 wards) | OpenCity.in KML | Area 720 km² from the polygons, matching the official 712.54 km² |
| 5 | Population: WorldPop R2025A, 2025, 100 m, constrained (India) | HTTP download, clipped to the study-area bounding box, national file deleted | ~6.04 M people inside BBMP; scaled to the Census 2011 control total (§4) |
| 6 | Candidate dark-store sites: OpenStreetMap grocery/convenience shops and warehouses | Geofabrik dated extract `southern-zone-261005.osm.pbf` (md5 checked), filtered with pyosmium; 1,480 sites in BBMP → 1,133 candidates | The live Overpass API was tried first; all public instances returned 504 or timed out on 2026-10-06, so we used a dated extract, which is also easier to cite |
| 7 | Road-distance correction | OSRM demo server, 40-cell random sample | Median road/straight-line detour ratio (`processed/detour_calibration.json`) |
| 8 | Built the model instance | `scripts/build_instance.py` | `processed/blr_*.csv`, `results/instance_summary.json` |

## 2. Sources

| Key in MANIFEST | Source | Licence | Used for |
|---|---|---|---|
| `worldpop` | WorldPop Global2 R2025A, India 2025, 100 m constrained | CC BY 4.0 | Spatial distribution of demand |
| `bbmp_wards_2022` | OpenCity.in, BBMP Ward Map 2022 (credit: Devdatta Tengshe) | Public domain (per listing) | Study-area boundary, ward reporting |
| `osm_candidate_sites` | © OpenStreetMap contributors via a Geofabrik extract | ODbL 1.0 | Candidate dark-store locations |
| OSRM sample (`processed/osrm_sample.json`) | router.project-osrm.org (OSM data) | ODbL data; demo-server terms | Detour factor only |
| Census 2011 control total | Census of India 2011: BBMP population 8,443,675 | Public | Scaling WorldPop |
| `kaggle:*` | Kaggle (licences "other"/MIT, see manifest) | as listed | **Audit only**; the illustrative peak-hour range |

## 3. Data audit: why the Kaggle data is not used for the model

`results/data_audit_kaggle.json` records the evidence:

- **Food Delivery Dataset (both uploads):**
  - In **98.4%** of rows, the delivery point is the restaurant point plus an *identical* lat/lon offset taken from 13 values (0.01–0.14°). The delivery geometry is therefore synthetic, and the distances and speeds derived from it are meaningless.
  - 3,640 rows have restaurant coordinates near (0, 0), and 431 rows have negative coordinates.
  - Road-traffic level is fully determined by order hour (every hour has a single level ≥90% of the time), and there are no orders between 01:00 and 07:00. The temporal fields are generated too.
- **Blinkit Sales Dataset:** **100%** of customer emails use RFC 2606 example domains (example.com/.org) with Faker-style names, so the dataset is synthetic.
- **Retained:** only the hourly order profile (`processed/order_hour_profile.csv`, peak/mean ≈ 1.8), and only as an *illustrative* upper value for the peak-hour multiplier sensitivity range. It is never treated as calibrated evidence.

Report this audit in the paper; data scrutiny counts under "data quality" in the rubric.

## 4. Processing decisions (assumptions to state in the paper)

| Decision | Value | Justification |
|---|---|---|
| Demand cell size | 5×5 WorldPop pixels ≈ 0.46 km | Small relative to dark-store radii of 1.5–3 km; keeps the MILP tractable |
| Demand cell inclusion | Cell centroid inside the BBMP union polygon; population > 0 | — |
| Population scaling | WorldPop × (8,443,675 / WorldPop BBMP sum) | WorldPop R2025A caps at ~140 people/ha in dense cores and totals ~6.0 M, below Census 2011. We keep its spatial pattern and use the census total as a conservative control (no post-2011 census exists) |
| Candidate sites | OSM supermarket/convenience/grocery/greengrocer shops and warehouse buildings, de-duplicated to one per ~165 m square (mean position) | Dark stores are leased in existing commercial or warehouse stock. Keeping true coordinates avoids lattice artefacts (snapping to the demand grid made nearby radii give identical results). OSM completeness varies by area (a limitation; see the E1-grid robustness run) |
| Road distance | Haversine × median OSRM detour ratio | The OSRM demo has only a car profile and free-flow speeds; we reuse only the ratio. Rider speed is a policy parameter |

## 5. Model parameters and their derivation

Each value is in `config/project.yaml`. Source quality: **P** = primary (company filing or CEO statement); **S** = secondary (press, analyst or industry blog); **A** = our assumption, covered by the sensitivity analysis.

| Parameter | Config key | Base (range) | Derivation | Q |
|---|---|---|---|---|
| Delivery promise | `promise_min` | 10, 15, 20, 30 min | Policy scenarios: claim withdrawn Jan 2026; Parliamentary panel, Aug 2026 | — |
| Safe rider speed | `rider_speed_kmh` | 15 (12–20) km/h | Zepto CEO, Apr 2022: average distance 1.8 km, so a 10-min delivery needs "<15 kmph". Forbes 2024: Zepto median 11 min, 1.5 km | P/S |
| Pick + pack | `pick_pack_min` | PERT (1.3, 2, 4) min | Zepto: packed "within 76 seconds" (Business Today, via Contrary Research). Grofers/Blinkit CEO, Aug 2021: "pack most orders under 2.5 minutes" | P/S |
| Assignment, handover | `rider_assign_min`, `handover_min` | PERT (0, 0.5, 2), (0.5, 1, 2) | — | A |
| Bengaluru daily orders | `bengaluru_daily_orders` | 600k (450k–750k) | Stores × orders/store/day: Blinkit 165 × 1,597 + Zepto 159 × 1,343 + Instamart 116 × 1,089 ≈ **603k**. Blinkit 1,597 = Eternal Q1 FY27 net order value/store/day ₹8.27 L ÷ AOV ₹518 (cross-check: 331 M orders ÷ 91 days ÷ ~2,340 stores ≈ 1,550). Instamart 1,089 = Swiggy Q1 FY27 shareholder letter (reported directly). Zepto = mean of the two (A). Store counts: quickcommercemap.com snapshot 2026-07-10 (S) | P/S/A |
| Peak-hour share | `peak_hour_share` | 0.10 (0.08–0.12) | Evening peak 5–11 pm (Blinkit operations head, via ITLN); busiest single hour 8 pm (Flipkart Minutes). No published hourly share, so it is a range | S/A |
| Current dark stores in Bengaluru | `current_dark_stores_bengaluru` | 440 | quickcommercemap.com (Blinkit 165, Zepto 159, Instamart 116), 2026-07-10 | S |
| Store fixed cost | `dark_store_fixed_cost_inr_month` | ₹8 L (6–11 L) | Opex: area ≈ 4,200 sq ft (Swiggy letter: 4.92 M sq ft ÷ 1,171 stores; P) × rent ₹60–100/sq ft (S) = ₹2.5–4.2 L; staff ₹1.5–2.4 L (S); utilities ₹0.4 L (S). Capex: Eternal steady-state ₹1–2.5 cr/store (P) ÷ 60 months = ₹1.7–4.2 L. Total ₹6.1–11.2 L | P/S |
| Rider cost | `rider_cost_inr_hour` | ₹125 (102–154)/logged-in hour | Eternal CEO factsheet (Jan 2026): average ₹102 per logged-in hour in 2025 (Zomato network; P). Upper value ₹40k/month ÷ 260 h ≈ ₹154 (S) | P/S |
| Rider utilisation | `rider_utilisation` | 0.6 (0.5–0.7) | Busy share of logged-in time | A |

**Validation:** in E1 (10 min, 15 km/h), the implied rider cost is ≈ ₹32 per order, inside the reported per-order pay of ₹25–35 (S). The demand and cost inputs are mutually consistent.

### Sources to add to Mendeley (grey literature; cite in §4 of the paper)

- Eternal Ltd, Q1 FY27 shareholder letter (July 2026). Figures as reported by MediaNama, "7 key takeaways from Eternal Q1 FY27 earnings call". **Download the letter itself from BSE/NSE and cite that.**
- Swiggy Ltd, Q1 FY27 Letter to Shareholders, NSE filing, 30 Jul 2026: `nsearchives.nseindia.com/corporate/SWIGGY_30072026154100_Covering_Letter_Letter_to_Shareholders_-_signed.pdf`. Quick-commerce table: orders/dark store/day 1,089; 1,171 stores; 4.92 M sq ft.
- Business Today (2 Jan 2026): Deepinder Goyal on delivery partner earnings (₹102/h).
- Zepto CEO statement, Apr 2022 (1.8 km, <15 km/h): via Global Indian / Outlook Business. **Find the original LinkedIn or X post.**
- Contrary Research, *Zepto* report (citing Forbes 2024 and Business Today).
- India.com / Inc42 (Aug 2021): Albinder Dhindsa statement on 2.5-minute packing.
- quickcommercemap.com, Bangalore platform pages, snapshot 2026-07-10. This is third-party scraped data: say so.
- Outlook Business (Jan and Aug 2026): 10-minute claim withdrawal; Parliamentary Standing Committee.

### Still open

- **Actual dark-store locations.** OSM tags only 5 of them. Options:
  - (a) the quickcommercemap Bangalore pass (₹999, about 200 m accuracy plus addresses), which needs a group decision;
  - (b) geocode published store address lists, e.g. the myhq Instamart list, with Nominatim;
  - (c) skip it and benchmark only against the count of 440.
  - With (a) or (b) we could compare the real network's coverage with the optimised one, a strong results section.

## 6. Summary statistics

From `results/instance_summary.json` (build of 2026-10-06):

| Item | Value |
|---|---|
| Wards (BBMP 2022) | 243 |
| Study area | 719.9 km² |
| Demand cells (~0.46 km) | 3,426 |
| Population, WorldPop R2025A inside BBMP | 6,044,607 |
| Population after scaling (Census 2011 control) | 8,443,675 (×1.3969) |
| OSM sites inside BBMP | 1,480 (supermarket 671, convenience 428, greengrocer 305, warehouse 58, grocery 18) |
| Candidate sites after ~165 m de-duplication | 1,133 |
| Road detour ratio (OSRM, 172 pairs, 0.5–6 km) | median 1.57 (IQR 1.41–1.81) |
