# Search protocol

Fill this in **before** running the final search (PLAN.md Phase 2). It becomes the
methodology section of the paper. Values must match `config/project.yaml`.

| Item | Value |
|---|---|
| Database(s) | TODO(human): EBSCOhost (+ Scopus / WoS / ScienceDirect?) |
| Search string (exact) | TODO(human): output of `make search-string` |
| Fields searched | TODO(human): e.g. title, abstract, keywords |
| Date range | TODO(human) |
| Language | English |
| Document type | Academic journals only |
| Sort order | Newest (or oldest) first, 50 results per page |
| Date search executed | TODO(human) |
| Records identified | TODO(human), screenshot: `screenshots/` |

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
| `review_only` | TODO(human): keep or exclude review articles? |
| `no_access` | Full text unobtainable (only if full text is required) |

## Screening rules

- Screen page by page in EBSCO order; record `search_page` for every record.
- `duplicate` = yes for repeats across pages/databases (keep the first copy).
- `decision` = include / exclude. Exclusions need a code from the table above.
- Disagreements: second screener decides; note in `notes`.

## RIS export log

| File | Records | Exported by | Date |
|---|---|---|---|
| `raw/ebsco_001-150.ris` | | | |
