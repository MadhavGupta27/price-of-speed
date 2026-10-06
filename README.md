# OR Group Project: bibliometric review + optimisation case study

Code, data and analysis for the OR research paper. The full plan is in [`PLAN.md`](PLAN.md); the assignment brief is `OR Project Guidelines.pdf`.

## Setup

Requires [uv](https://docs.astral.sh/uv/), R ≥ 4.3 and pandoc. Optional: `pandoc-crossref` for numbered figure references.

```bash
make setup     # Python deps (PuLP + HiGHS solver) and R deps (bibliometrix)
make test      # model and pipeline tests
make todo      # every input the group still has to provide
```

## Workflow

| Phase (PLAN.md) | Human does | Then run |
|---|---|---|
| 1 Topic | Fill `config/project.yaml` (topic, RQs, search terms, years, model family) | `make search-string` |
| 2 Search & screen | Run the EBSCO search, screenshot it into `biblio/screenshots/`, fill `biblio/search_protocol.md`, log every record in `biblio/screening_log.csv`, export RIS to `biblio/raw/`, curate in Mendeley, export `biblio/exports/final_library.bib` | `make prisma` |
| 3 Bibliometrics | — | `make biblio-import` |
| | Clean `biblio/exports/biblioshiny_export.xlsx`; pull Google Scholar counts with Publish or Perish into `biblio/exports/publish_or_perish.csv` | `make citations RETRIEVED=YYYY-MM-DD` then `make biblio-analysis` |
| 4 Core papers | Mark `selected` in `biblio/core_candidates.csv`; read the papers and fill `biblio/core_papers_matrix.csv` | — |
| 5 Data | Put raw files in `data/raw/`, document them in `data/README.md` | — |
| 6 Model | Adapt the chosen model in `src/orpaper/models/` to the case | `make toy` |
| 7 Experiments | Set real parameter grids in `experiments/run_sensitivity.py` | `make sensitivity` |
| 8 Paper | Write `paper/paper.md`; copy the final `.bib` to `paper/references.bib`; put the instructor's template at `paper/template.docx` | `make paper` |

`FAMILY=transportation|assignment|cpm_pert|vrp` overrides the model family for `make toy` and `make sensitivity`.

## Layout

```
config/project.yaml        all human decisions (search terms, years, model family, solver)
biblio/                    bibliographic dataset: raw RIS, screening log, protocol, exports, figures
biblio/R/                  bibliometrix import (01) and analysis (02)
scripts/                   PRISMA counts and diagram; Google Scholar citation merge + core shortlist
src/orpaper/models/        transportation (LP + NW corner/VAM), assignment (IP), CPM/PERT + crashing LP, CVRP (MILP + nearest-neighbour)
src/orpaper/data/          seeded synthetic instances; OSRM road matrices with haversine fallback
src/orpaper/sensitivity.py one-way sensitivity runner and plot
experiments/               toy run and sensitivity analysis -> results/
data/                      case-study data (raw/ is never hand-edited) + provenance README
paper/                     paper.md (pandoc) -> paper/build/paper.docx
```

## Data sources

See [`data/README.md`](data/README.md). Bibliographic data comes from EBSCOhost (see `biblio/search_protocol.md`) and Google Scholar citation counts via Publish or Perish.
