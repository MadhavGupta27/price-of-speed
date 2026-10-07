# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Operations Research group project. **Topic chosen:** *The Price of Speed*, covering quick-commerce dark-store location, rider sizing, replenishment and fulfilment-time risk under delivery-promise policy, with a Bengaluru case. Rationale is in `docs/topic-proposal.md` and the section, model and experiment plan in `docs/paper-plan.md`. The project combines a **bibliometric literature review** plus an **applied OR model** (transportation, assignment, LP/MILP, CPM/PERT), written up as a paper of at most 12 pages. The brief is `OR Project Guidelines.pdf`. `PLAN.md` is the phase-by-phase work plan; `README.md` maps each phase to its human step and `make` target.

The scaffold is complete, but most content is still a human decision. Every placeholder is marked `TODO(human)`, and `make todo` lists them. Don't invent research content (topic, search terms, citations, results interpretation) — fill these only from the group's actual inputs.

## Commands

```bash
make setup                         # uv sync + R packages into R_LIBS_USER
make test                          # uv run pytest -q
uv run pytest tests/test_vrp.py::test_routes_feasible_and_beat_heuristic   # single test
make data                          # fetch raw inputs (+MANIFEST), audit Kaggle, build Bengaluru instance
make case                          # first-pass set-covering sweep (superseded by make experiments)
make experiments                   # paper experiments: M1-cost design grid, grid robustness, PERT, assignment, transport, tornado
uv run python experiments/run_design.py --only assign --reuse   # rerun one experiment on saved E1 designs
make paper                         # export numbers/tables -> compile paper/main.tex with tectonic -> paper/build/main.pdf
make toy FAMILY=vrp                # toy instance + baseline -> results/toy_<family>.json
make sensitivity FAMILY=cpm_pert   # one-way sensitivity -> results/sensitivity_<family>.{csv,png}
make biblio-import                 # Mendeley .bib -> bibliometrix -> biblio/exports/biblioshiny_export.xlsx
make biblio-analysis               # figures -> biblio/figures/, tables -> results/
make prisma                        # biblio/screening_log.csv -> PRISMA counts + flow diagram
make citations RETRIEVED=YYYY-MM-DD  # merge Publish-or-Perish GS counts, build core-paper shortlist
make paper                         # paper/paper.md -> paper/build/paper.docx (pandoc --citeproc)
```

## Architecture

There are two independent pipelines, matching the two datasets the paper needs:

1. **Bibliographic pipeline** (literature review):
   - Humans run the EBSCO search and fill `biblio/screening_log.csv`, using the exclusion codes in `biblio/search_protocol.md`.
   - Mendeley export → `biblio/R/01_import.R` → hand-cleaned Excel → `scripts/merge_citations.py` adds Google Scholar counts (column `GS_TC`) → `biblio/R/02_analysis.R`.
   - `02_analysis.R` prefers `records_with_gs.xlsx` when it exists and substitutes `GS_TC` for `TC`.
   - The Python side (`src/orpaper/biblio.py`) does only the bookkeeping: PRISMA counts, DOI/title matching, and a citations-per-year shortlist.
2. **Optimisation pipeline** (case study):
   - `src/orpaper/models/*` are self-contained PuLP models. Each returns a result dataclass and raises if the solve isn't `Optimal`.
   - `experiments/` wires models to `data/synthetic.py` instances; replace these with real loaders from `data/processed/` once data exists.
   - `sensitivity.one_way` records exceptions (e.g. an infeasible crash deadline) as rows instead of aborting.

3. **Case pipeline** (Bengaluru):
   - `scripts/fetch_data.py` (provenance → `data/raw/MANIFEST.json`) → `scripts/audit_kaggle.py` → `scripts/build_instance.py` (uses `src/orpaper/data/geo.py`).
   - Outputs: `data/processed/blr_demand_cells.csv` (WorldPop cells, scaled to the Census 2011 total) and `blr_candidates.csv` (de-duplicated OSM sites).
   - `experiments/run_case.py` runs `models/covering.py` (set/maximal covering) plus cycle-time rider sizing.
   - The procedure log and all assumptions are in `data/README.md`.

4. **Paper** (`paper/`, LaTeX):
   - `main.tex` inputs `sections/*.tex`.
   - Every result number is a macro from `paper/generated/numbers.tex`, and the tables are `generated/tab_*.tex`, both written by `scripts/export_numbers.py` from `results/`. Never hard-code result numbers in the `.tex` files; add a macro instead.
   - Figures go to `paper/figures/` (written by `experiments/run_design.py`).
   - `\todo{}` marks pending human or pipeline input.
   - The main model is `models/design.py` (coverage-constrained facility location, M1-cost); `models/covering.py` is the first-pass set covering.

5. **Literature pipeline (as run):**
   - `scripts/openalex_search.py` → `biblio/openalex_records.csv`.
   - LLM-assisted screening decisions are in `biblio/screening/`, merged into `biblio/screening_log.csv` and `biblio/screened_records.csv`.
   - `scripts/openalex_to_bibliometrix.py` → `biblio/exports/biblioshiny_export.xlsx`, RIS and bib.
   - `biblio/R/02_analysis.R` → figures and clusters.
   - `scripts/build_lit_assets.py` → the core-paper matrix, `paper/lit.bib`, `generated/tab_core.tex` and `generated/biblio_numbers.tex`.

`config/project.yaml` is the single source of truth. It holds the search terms and years, the `model_family` that `make toy`/`make sensitivity` default to, the solver, and the seed. `make search-string` composes the Boolean string and always keeps the mandatory `"operations" AND "research"`.

## Gotchas (verified)

- **PuLP pinned `<3`.** PuLP 4 rewrote its API (Rust core; `LpVariable(..., cat=)` no longer works) and ships no CBC. The solver is HiGHS via `highspy`; CBC is also available under 2.x.
- **`PYTHONPATH=src` is set explicitly** in the Makefile and in pytest's `pythonpath`. On this machine the uv venv's `.pth` files get the macOS `hidden` flag, which Python 3.13 silently skips, so the editable install doesn't import. Run ad-hoc scripts with `PYTHONPATH=src uv run python …`.
- **R packages go in `R_LIBS_USER`**, because the system R library isn't writable. The R scripts prepend it to `.libPaths()`.
- **Mendeley BibTeX in bibliometrix:**
  - Use `dbsource="scopus"`. `01_import.R` falls back to `generic` if that fails.
  - Mendeley `keywords` land in `ID`, not `DE`; the import script copies them across.
  - bibliometrix fills missing `CR` with `"none"` and `TC` with `0`, so `results/field_completeness.csv` treats those as missing.
  - Expect no cited references, so co-citation analysis is unavailable unless records are re-pulled from Scopus/WoS.
- **The Kaggle delivery datasets are synthetic.** Food-delivery geometry is the restaurant point plus a fixed diagonal offset, and traffic level is fixed by hour; the Blinkit data uses Faker customers. Never use them for geography or speeds (see `results/data_audit_kaggle.json`).
- **The WorldPop server rejects HTTP range requests**, so `/vsicurl` fails. The fetch script downloads the 780 MB national file, clips it to the bounding box, and deletes it. WorldPop undercounts BBMP (~6.0 M), so the build scales it to the Census 2011 total.
- **Public Overpass instances were down** (504/timeouts). OSM sites come from a dated Geofabrik extract filtered with pyosmium instead.
- **Cost per order in E1 is per *served* order.** At T = 10, the unreachable 15% of residents is excluded, so compare coverage alongside cost. The promise mainly changes coverage; rider speed changes cost.
- **The M1-cost solve grows with the reachable arcs.** It takes 82 s at T = 30. With every demand cell as a candidate (3,426 sites), it ran past 11 minutes at T = 10, so the grid robustness run uses a ~0.9 km candidate lattice.
- **Don't snap candidate sites to the demand grid.** Lattice distances made different radii produce identical covering results.
- **PuLP reports a HiGHS time limit as LpStatus "Optimal".** Only `prob.sol_status` (`LpSolutionOptimal` vs `LpSolutionIntegerFeasible`) distinguishes the two. Use `orpaper.solver.solution_status`/`check_optimal`, which do this; every result CSV has a `status` column.
- **The M1-cost LP relaxation can split a demand cell between equal-cost stores** (a degenerate optimum). A cell is served iff its slack `u_i < 0.5`; take the largest `x_ij` as its store and compute rider cost from the objective term (`models/design.py`). Thresholding `x > 0.5` undercounts coverage (regression test: `test_tied_stores_count_cell_as_served`).
- **OpenAlex without an API key** shares a small daily per-IP budget. The key is read from `.env` (`OPENALEX_API_KEY`, gitignored). Queries with more than 5 Boolean operators are throttled, so each topic term is queried separately and the clauses are applied locally.
- **Tectonic's BibTeX can't find `.bib` files in subdirectories.** The generated bibliography is therefore `paper/lit.bib`, not `paper/generated/`.
- **LaTeX macro names can't contain digits** (e.g. `\BibSinceTwentyOnePct`, not `...2021...`).
- `tests/fixtures/sample_mendeley.bib` contains **fake** records for pipeline testing. Never cite them, and never copy them into `paper/references.bib`.

## Deliverable constraints (from the PDF)

- Paper ≤12 pages, using the instructor's template (not yet received; put it at `paper/template.docx`).
- Deck ≤12 slides for 20 minutes.
- Code repo with a README covering how to run it and where the data came from.
- Mendeley `.bib`/`.ris` export.
- 10–20 core papers.
- A sensitivity analysis on key parameters is expected.
- Paper rubric (10 marks): novelty & intro, lit review & methodology, structure & clarity, discussion & future agenda, publication — 2 each. Project rubric (100 points): model 20, results 20, lit review 15, data/reproducibility 15.
