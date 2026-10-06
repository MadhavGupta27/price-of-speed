# Research Paper Work Plan

Derived from `OR Project Guidelines.pdf` (Dr Richa's bibliometric process, pp. 18; Dr Pradhan's project guidance and rubric, pp. 19–23; Mendeley notes and paper rubric, pp. 24–25).

The paper combines two things, and each needs its own dataset:

| Dataset | What it is | Feeds |
|---|---|---|
| **A. Bibliographic dataset** | Journal-article records from EBSCO (+ Scopus/WoS), cleaned in Mendeley, analysed in Biblioshiny | Literature review, bibliometric figures, research gaps |
| **B. Case-study dataset** | Real or synthetic operational data (demand, distances, durations, costs) | OR model, computational experiment, sensitivity analysis |

---

## Phase 0 — Setup

- [ ] Assign roles across the 5–6 members: search/screening lead, Biblioshiny/analysis lead, modelling lead, data lead, writing/editing lead, presentation lead.
- [ ] Each member installs **Mendeley Desktop** and creates an account; create one shared **Mendeley group** for the project.
- [ ] Each member gets **EBSCO** access through the library database and creates an EBSCO account.
- [ ] Install **R + RStudio** and the `bibliometrix` package (`install.packages("bibliometrix")`; launch with `library(bibliometrix); biblioshiny()`).
- [ ] Install Python + an OR solver (OR-Tools or PuLP are free; Gurobi has free academic licences).
- [ ] Create the shared repo (`git init` here — this folder currently sits inside an unrelated parent repo). Suggested layout: `biblio/` (raw RIS, exports, screening log, screenshots), `data/raw`, `data/processed`, `model/` (notebooks), `paper/`, `figures/`.
- [ ] **Get the paper template from the instructor.** Step 15 says "write as per the template given", but the template is not in the PDF.

## Phase 1 — Topic and research questions

- [ ] Pick a topic. It must be **novel and relevant**, not chosen just because material is plentiful (Step I). The 14 suggested topics cover transportation, assignment, LP/MILP and CPM/PERT. Novelty counts for 2/10 on the paper rubric.
- [ ] Write 2–3 research questions covering (a) the literature (trends, dominant methods, gaps) and (b) the model (what the optimisation answers).
- [ ] Run a **pilot search** in EBSCO to check the volume. You want enough records for meaningful bibliometrics (roughly a few hundred), plus 10–20 core papers for deep review. If the count is too low, broaden the keywords or the year range; if it is too high, narrow them.
- [ ] Check early that you can get usable case-study data for the topic (Phase 5). A topic with no obtainable data is a trap.
- [ ] Fix the scope: year range, geography (if any), problem variant and assumptions.

## Phase 2 — Build the bibliographic dataset (Dataset A)

Write the search protocol down **before** searching. It becomes the methodology section.

- [ ] **Search string:** `"Operations" AND "research"` is **mandatory** (Step 4), combined with topic and method terms, e.g. `"operations research" AND ("vehicle routing" OR "last-mile") AND ("mixed integer" OR "linear programming")`. Record the exact string and the date it was run.
- [ ] **EBSCO settings:** 50 results per page; sort by newest or oldest instead of relevance, so paging is deterministic.
- [ ] **Inclusion filters:** academic journals only, English only, fixed start and end years.
- [ ] **Screenshot** the search with the final count (Step 6). This is required evidence.
- [ ] Optionally repeat the search in Scopus/WoS/ScienceDirect for coverage (Pradhan guidance). Record those counts separately.
- [ ] **Screen page by page** (Step 7). Add the kept records to the folder. For every exclusion, log title, **document type and reason** (documentaries, case studies, introductions, student theses, editorials, out of scope). Keep it in `biblio/screening_log.xlsx`.
- [ ] Turn the counts into a PRISMA-style flow: identified, then duplicates removed, then screened, then excluded (with reasons), then included. This makes a strong methodology figure.
- [ ] **Export RIS** in batches of **≤150 records** (Step 8). Name the files in sequence (`ebsco_001-150.ris` …).
- [ ] Import all RIS files into the Mendeley project folder (Step 9). Remove duplicates.
- [ ] Attach **full-text PDFs** where available (Step 10). Use the library's subscriptions, open-access versions, author copies or Unpaywall. The PDF mentions Sci-Hub; check your institution's policy before relying on it.
- [ ] **Verify metadata** for every record with "view research catalogue entry" (Step 11): authors, year, journal, DOI, keywords and abstract. Missing keywords and abstracts degrade the Biblioshiny output.
- [ ] Export the final dataset as **`.ris` and `.bib`** from Mendeley (Step 12). This also covers the Mendeley-export deliverable.

## Phase 3 — Bibliometric analysis

- [ ] Load the `.bib` into **Biblioshiny** (Step 13).
  - **Risk — test this on day one with a small export.** Bibliometrix is built for Scopus, WoS and similar exports. A Mendeley/EBSCO BibTeX may import with missing fields, especially cited references, so co-citation analysis may not work. If import fails or comes out thin, try the generic or Scopus BibTeX option, or re-pull the same records from Scopus. Note any limitation in the paper.
- [ ] Export the Biblioshiny **Excel** data sheet (Step 14) and clean it:
  - [ ] Remove duplicates and fix errors in the records.
  - [ ] Normalise author names, journal names and keyword synonyms (e.g. "VRP" = "vehicle routing problem").
  - [ ] Add a **Google Scholar citation count** for each article, with the retrieval date. Harzing's *Publish or Perish* can batch-pull these instead of a manual lookup per paper.
- [ ] Re-run the analyses on the cleaned data and produce the figures:
  - [ ] Annual publication trend (growth rate)
  - [ ] Most productive authors, countries and institutions
  - [ ] Leading journals (Bradford's law, optional)
  - [ ] Most-cited papers (Google Scholar counts)
  - [ ] Keyword frequency / word cloud and keyword co-occurrence network
  - [ ] Thematic map and/or thematic evolution (emerging vs declining themes)
  - [ ] Co-authorship / collaboration network
  - [ ] VOSviewer maps (optional, Pradhan guidance)
- [ ] Select the **10–20 core papers** (highly cited, recent and highly relevant) for deep reading.

## Phase 4 — Content review of the core papers

- [ ] Read each core paper and fill in a coding matrix (`biblio/core_papers_matrix.xlsx`). Columns: problem type, OR method (LP/MILP/assignment/CPM/PERT/heuristic), solver/software, data (real/synthetic, size), key findings, limitations.
- [ ] Tag the papers in Mendeley by theme and method, and annotate key findings (pp. 24–25).
- [ ] Synthesise: dominant methods, how they evolved, under-studied combinations and **research gaps**. These justify both the model and the future research agenda.

## Phase 5 — Acquire the case-study dataset (Dataset B)

- [ ] List the parameters the model needs: nodes/locations, demand, capacities, distances/travel times, costs, time windows, activity durations (for CPM/PERT: optimistic, most likely and pessimistic times; crash costs).
- [ ] Source the data, in order of preference:
  1. Government open-data portals (transit, freight, health), country-specific
  2. Kaggle datasets (vehicle routing, traffic, transit)
  3. UCI Machine Learning Repository
  4. OpenStreetMap + OSRM for real road distance and time matrices between real coordinates
  5. Published benchmark instances from the core papers
  6. **Synthetic data**, generated with a fixed random seed, with ranges justified from the literature or real data
- [ ] Record the provenance of every source (URL, access date, licence, period covered) in `data/README.md`. This is required.
- [ ] Preprocess: clean, aggregate, build distance/cost matrices and convert units. Keep it scripted (no manual edits) so it is reproducible.
- [ ] Produce summary statistics for the paper (n, period, key fields).

## Phase 6 — Model formulation and implementation

- [ ] Write the mathematical model: sets/indices, parameters, **decision variables, objective, constraints**, and every **assumption** stated explicitly. Model formulation is worth 20/100.
- [ ] Justify the method choice with the literature (e.g. "MILP used by X of the 20 core papers; exact solvers tractable at this size").
- [ ] Implement it in a Python notebook (OR-Tools / PuLP / Gurobi). Excel Solver is acceptable for a toy check.
- [ ] Solve a **toy instance first** and verify by hand (Northwest Corner/VAM/MODI, Hungarian method or CPM forward/backward pass, as relevant). Then scale up.
- [ ] Validate: feasibility checks, sanity checks on the objective, and a comparison against a baseline (current practice, greedy heuristic or textbook method).

## Phase 7 — Computational experiments and sensitivity analysis

- [ ] Define the instances (toy → medium → full) and the scenarios.
- [ ] Record the objective value, solve time, optimality gap and solver settings. These feed the backup slide B.
- [ ] Run a **sensitivity analysis** on 2–3 key parameters: fleet size, vehicle capacity, penalty weights, demand ±%, cost changes; and crash cost or duration variance for CPM/PERT. Explicitly expected; Results and sensitivity are worth 20/100.
- [ ] Produce the results tables and figures, and interpret what changed and why.
- [ ] Derive the **managerial implications**: concrete, actionable recommendations.

## Phase 8 — Write the paper

Use the instructor's template. Max **12 pages**. Use the Mendeley Word plug-in for citations, with one consistent style. The Manchester Academic Phrasebank (phrasebank.manchester.ac.uk) helps with phrasing.

| Section | Content | Source phase |
|---|---|---|
| Title, Abstract, Keywords | Problem, method, key result, contribution | All |
| 1. Introduction | Relevance, **novelty**, research questions, contribution, paper outline | 1, 4 |
| 2. Literature review | Bibliometric findings plus thematic synthesis of the core papers; gaps | 3, 4 |
| 3. Research methodology | Search protocol, filters, screening/PRISMA flow, tools (Mendeley, Biblioshiny); modelling approach | 2, 3 |
| 4. Problem description and model | System description, assumptions, mathematical formulation | 6 |
| 5. Data | Sources, preprocessing, summary statistics | 5 |
| 6. Solution approach | Solver/algorithm, implementation, instance sizes | 6 |
| 7. Results and sensitivity analysis | Tables/figures, robustness | 7 |
| 8. Discussion | Managerial implications, limitations, **future research agenda** (from the gaps) | 4, 7 |
| 9. Conclusion | Answers to the research questions, recommendations | All |
| References | Mendeley-generated | 2 |
| Appendix (if room) | Search screenshot, exclusion summary, extra tables | 2 |

- [ ] Draft in parallel by section owner, then have one editor unify voice, notation and figure style.
- [ ] Cite sources on every figure/table taken from elsewhere; make sure each bibliometric figure has a caption that interprets it.

## Phase 9 — Review and submission

- [ ] Self-grade against **both rubrics**:
  - Paper (10 marks, p. 25): novelty and introduction (2) · literature review and methodology (2) · structure and clarity (2) · discussion and future research agenda (2) · **publication (2)**
  - Project (100 pts, pp. 20–21): problem definition 10 · literature/bibliometric 15 · model 20 · data and reproducibility 15 · results 20 · presentation 10 · Q&A 10
- [ ] "Publication" earns marks, so pick a **target journal or conference** early and format for it. Ask the instructor what counts (submission vs acceptance).
- [ ] Check the page limit, reference consistency, figure readability and notation consistency.
- [ ] Check reproducibility: a fresh clone + README → notebooks run end to end.
- [ ] Submission checklist (p. 21):
  - [ ] Final report (≤12 pages)
  - [ ] Slide deck (≤12 slides; 20 min, with backup slides A/B/C)
  - [ ] Code repository link + README (how to run, data origin)
  - [ ] Data files or data-source links
  - [ ] Mendeley `.bib`/`.ris` export or shared group library link
  - [ ] Search screenshot and exclusion log (evidence for Steps 6–7)

---

## Critical path and risks

1. **Topic choice → pilot search → data availability check.** Do all three before committing to a topic.
2. **Biblioshiny import of the Mendeley BibTeX.** Test it with 20 records before screening hundreds.
3. **Metadata verification and Google Scholar citations** take the most manual time. Split the records across members.
4. **Model + sensitivity analysis** carry 40/100 points. Start on the toy instance while screening is still under way; the two tracks are independent.

## Open questions for the instructor

- Where is the paper template (Step 15)?
- Is there a required year range or a minimum number of records?
- What counts for the "Publication (2)" criterion?
- Which rubric governs the paper: the 10-mark paper rubric, the 100-point project rubric, or both?
