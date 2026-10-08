# Licensing

This repository mixes original work and third-party data, each under its own terms.

| Content | Licence | Full text |
|---|---|---|
| Source code (`src/`, `scripts/`, `experiments/`, `biblio/R/`, `tests/`, `Makefile`) | MIT | [`LICENSE`](LICENSE) |
| Manuscript text, tables and figures (`paper/`, `submission/`, `docs/`) | CC BY 4.0 | [`licenses/CC-BY-4.0.txt`](licenses/CC-BY-4.0.txt) |
| Data derived from OpenStreetMap (`data/raw/osm/`, `data/processed/blr_osm_sites.csv`, `blr_candidates.csv`, `osrm_sample.json`, `detour_calibration.json`) | ODbL 1.0 (share-alike) | [`licenses/ODbL-1.0.txt`](licenses/ODbL-1.0.txt), [`data/LICENSE.md`](data/LICENSE.md) |
| Population data derived from WorldPop (`data/raw/worldpop/`, `data/processed/blr_demand_cells.csv`) | CC BY 4.0 | [`licenses/CC-BY-4.0.txt`](licenses/CC-BY-4.0.txt) |
| BBMP ward boundaries (`data/raw/bbmp/`, `data/processed/blr_wards.csv`) | Public domain, as listed by OpenCity.in | — |
| Bibliographic metadata from OpenAlex (`biblio/`) | CC0 1.0 (OpenAlex data licence) | see note below |
| Springer Nature LaTeX class `sn-jnl.cls` (`submission/opsearch/template/`) | LaTeX Project Public License 1.3c | header of the file |
| Springer Nature bibliography styles (`submission/opsearch/template/*.bst`) | Distributed by Springer Nature for author use | — |

## Notes

- **The CC BY 4.0 grant on the manuscript covers this preprint version.** If the article is accepted, the publisher's licence or copyright agreement governs the published version.
- **OpenAlex** releases its metadata under CC0. Abstract text in `biblio/openalex_records.csv`, `biblio/screened_records.csv` and the Bibliometrix export may remain under the copyright of the original publishers. It is included only to document the screening and is not covered by the CC BY grant above.
- **Not redistributed:** the Kaggle datasets audited in `scripts/audit_kaggle.py` (licences "other"/MIT). Fetch them with `make data`.
- **Not redistributed:** the national WorldPop raster and the Geofabrik OSM extract. Both are downloaded, clipped or filtered, then deleted (`scripts/fetch_data.py`).
- **Facts, not licensed material:** figures quoted from company shareholder letters and press reports (orders, store counts, costs). Each is cited in `data/README.md` and the paper.

## Attribution required when reusing the data

- © OpenStreetMap contributors, available under the Open Database License (ODbL 1.0); routing via OSRM.
- WorldPop (2025). Global2 R2025A constrained population counts, India, 100 m. University of Southampton. CC BY 4.0.
- OpenCity.in, BBMP Ward Map 2022 (credit: Devdatta Tengshe).
