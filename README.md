# The Price of Speed

**Optimising Dark-Store Networks and Rider Assignment under Relaxed Delivery Promises in Indian Quick Commerce**

Operations Research group project: Madhav Gupta (28), Aadee Pardasani (01), Aashi Khuthia (06), Jiya Jagawat (23), Prishi Doshi (36), Aarushi Rakesh (05).

The paper is at [`paper/The_Price_of_Speed_final.pdf`](paper/The_Price_of_Speed_final.pdf). It combines two parts:

1. **A bibliometric review** of operations research on last-mile and on-demand delivery: 168 journal articles from 2015 to 2026.
2. **An optimisation case study** of a Bengaluru dark-store network built from public data. It asks how many stores and riders a 10-, 15-, 20- or 30-minute delivery promise needs at a safe rider speed, and what that costs.

## Headline results

- At a safe speed of 15 km/h, the cost-optimal network has about **240 stores**. It reaches **98.3%** of residents for any promise of 15 minutes or more.
- A **10-minute promise** cannot reach 13.3% of residents from mapped retail sites. Serving everyone within 10 minutes needs **61% more stores** and costs **8.4% more per order**.
- **Rider speed, not the promise, drives cost.** Capping speed at 15 km/h instead of 20 km/h raises cost per order by about **19%**.
- **A "realistic promise" policy** offers 10 minutes only where an address is reachable at safe speed, and 15 minutes elsewhere. It gives **86.7%** of residents 10-minute service at **4.2%** higher cost than a uniform 15-minute network.
- **The literature gap:** only 3 of 168 OR articles address quick commerce, none studies India, and only 4 consider courier welfare.

## Setup

Requires [uv](https://docs.astral.sh/uv/), R ≥ 4.3 and [Tectonic](https://tectonic-typesetting.github.io/).

```bash
make setup     # Python deps (PuLP + HiGHS) and R deps (bibliometrix)
make test      # model and pipeline tests
```

The literature search needs a free OpenAlex API key. Put it in a `.env` file (gitignored):

```
OPENALEX_API_KEY=...
```

## Reproducing the paper

| Step | Command | What it does |
|---|---|---|
| 1. Case data | `make data` | Downloads raw inputs (WorldPop 2025 population, BBMP 2022 wards, OpenStreetMap sites from a dated Geofabrik extract, OSRM sample) with provenance in `data/raw/MANIFEST.json`. Audits the Kaggle delivery datasets and builds the Bengaluru instance in `data/processed/` |
| 2. Experiments | `make experiments` | Network design over promise × speed, robustness with "store anywhere" candidates, PERT reliability, peak dispatch (assignment), replenishment (transportation), sensitivity tornado, store-count fragmentation and the realistic-promise policy. Results go to `results/`, figures to `paper/figures/` |
| 3. Literature | `make biblio-search` | OpenAlex search, merge of the screening decisions, Bibliometrix analysis, PRISMA diagram, core-paper table and bibliography |
| 4. Paper | `make paper` | Exports every result number as LaTeX macros (`paper/generated/`) and compiles `paper/main.tex` to `paper/build/main.pdf` |

Every number in the paper comes from `paper/generated/numbers.tex` and `paper/generated/biblio_numbers.tex`, so rerunning steps 1–4 regenerates the paper.

## Layout

```
config/project.yaml       topic, search protocol, case parameters, solver settings
data/                     case-study inputs; data/README.md documents sources, audit and every parameter
biblio/                   search protocol, screening log and decisions, core-paper matrix, exports (RIS/BibTeX)
biblio/R/                 bibliometrix import and analysis
scripts/                  data fetch/audit/build, OpenAlex search, screening merge, PRISMA, paper exports
src/orpaper/models/       design (coverage-constrained facility location), covering, transportation,
                          assignment, CPM/PERT, VRP
src/orpaper/data/         spatial preprocessing, OSRM matrices, synthetic toy instances
experiments/              run_design.py (main experiments), run_policy.py (fragmentation, realistic promise)
paper/                    LaTeX source, generated macros/tables, figures, final PDF
tests/                    tests for every model (brute force or hand-solvable instances) and the pipelines
docs/                     topic proposal and paper plan
```

## Journal submission

`submission/opsearch/` contains the submission package for *OPSEARCH* (Springer): the manuscript in the Springer Nature template, the upload bundle, the cover letter and a checklist. Rebuild it with `make submission`.

## Licences

- Code: MIT ([`LICENSE`](LICENSE)).
- Manuscript and figures: CC BY 4.0 (preprint version).
- OpenStreetMap-derived data: ODbL 1.0.
- WorldPop-derived data: CC BY 4.0.
- OpenAlex metadata: CC0.

Details and required attributions are in [`LICENSES.md`](LICENSES.md) and [`data/LICENSE.md`](data/LICENSE.md).

## Data and method notes

- **The Kaggle delivery datasets are synthetic** and are not used for geography or speeds. The evidence is in `results/data_audit_kaggle.json` and `data/README.md` §3.
- **The bibliometric search ran on OpenAlex.** EBSCOhost, prescribed by the course, needs an institutional login. Screening ran in two passes; every decision and rationale is in `biblio/screening/` and `biblio/screening_log.csv`.
- **Optimisation status:** all models are solved with HiGHS via PuLP, and solver status is reported honestly. 27 of 29 MILPs are proven optimal. Two maximal-covering runs hit the 600 s limit, and their coverage is reported as a lower bound.
