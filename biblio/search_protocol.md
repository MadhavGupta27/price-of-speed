# Search protocol

Fill this in **before** running the final search (PLAN.md Phase 2). It becomes the
methodology section of the paper. Values must match `config/project.yaml`.

| Item | Value |
|---|---|
| Database(s) | OpenAlex (run 2026-10-06). EBSCOhost is prescribed by the course but no institutional login was available; an EBSCO export can be swapped in through the same pipeline |
| Search string (exact) | output of `make search-string`; executed per topic term on OpenAlex title+abstract, method and mandatory clauses applied locally (see `scripts/openalex_search.py`) |
| Fields searched | Topic + method: title, abstract. Mandatory terms: title, abstract, journal name, keywords |
| Date range | 2015-2026 |
| Language | English |
| Document type | Academic journals only |
| Sort order | Newest (or oldest) first, 50 results per page |
| Date search executed | 2026-10-06 |
| Records identified | 7,576 (union) -> 715 (method) -> 216 (mandatory) -> 177 included; `results/search_log.json`, `paper/figures/prisma_flow.pdf` |

## Exclusion criteria

Use these codes in the `exclusion_reason` column of `screening_log.csv` so the
PRISMA counts group cleanly. Add codes here if needed, don't invent them ad hoc.

| Code | Meaning |
|---|---|
| `out_of_scope` | Not about the topic / not an OR application |
| `case_study` | Teaching case or practitioner case study |
| `introduction` | Editorial, special-issue introduction, preface |
| `thesis` | Student thesis or dissertation |
| `documentary` | Documentary, news, magazine item |
| `no_or_method` | Delivery topic, but no OR/optimisation model, algorithm or review of such (e.g. consumer survey, policy essay) |
| `review_only` | Not used: literature reviews of OR delivery methods are included and tagged `review` |
| `no_access` | Full text unobtainable (only if full text is required) |

## Screening rules

- Screen page by page in EBSCO order; record `search_page` for every record.
- `duplicate` = yes for repeats across pages/databases (keep the first copy).
- `decision` = include / exclude. Exclusions need a code from the table above.
- Disagreements: second screener decides; note in `notes`.
- 2026-10-06 run: title/abstract screening (four batches, criteria above); decisions and coding in `biblio/screening/decisions_*.json`. 24 records flagged uncertain were re-screened by an independent second pass (`biblio/screening/second_pass.json`), whose decision was adopted; 9 decisions changed (include -> exclude). Final: 168 included, 48 excluded.

## RIS export log

| File | Records | Exported by | Date |
|---|---|---|---|
| `raw/ebsco_001-150.ris` | | | |
