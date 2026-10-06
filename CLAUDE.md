# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An Operations Research group project: a **bibliometric literature review** plus an **applied OR model** (transportation, assignment, LP/MILP, CPM/PERT), written up as a paper of at most 12 pages. The brief is `OR Project Guidelines.pdf`. `PLAN.md` is the phase-by-phase work plan; `README.md` maps each phase to its human step and `make` target.

The scaffold is complete, but most content is still a human decision. Every placeholder is marked `TODO(human)`, and `make todo` lists them. Don't invent research content (topic, search terms, citations, results interpretation) — fill these only from the group's actual inputs.

## Commands

```bash
make setup                         # uv sync + R packages into R_LIBS_USER
make test                          # uv run pytest -q
uv run pytest tests/test_vrp.py::test_routes_feasible_and_beat_heuristic   # single test
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
- `tests/fixtures/sample_mendeley.bib` contains **fake** records for pipeline testing. Never cite them, and never copy them into `paper/references.bib`.

## Deliverable constraints (from the PDF)

- Paper ≤12 pages, using the instructor's template (not yet received; put it at `paper/template.docx`).
- Deck ≤12 slides for 20 minutes.
- Code repo with a README covering how to run it and where the data came from.
- Mendeley `.bib`/`.ris` export.
- 10–20 core papers.
- A sensitivity analysis on key parameters is expected.
- Paper rubric (10 marks): novelty & intro, lit review & methodology, structure & clarity, discussion & future agenda, publication — 2 each. Project rubric (100 points): model 20, results 20, lit review 15, data/reproducibility 15.
