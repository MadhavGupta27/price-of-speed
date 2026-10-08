# Paper plan: *The Price of Speed*

Working title: **The Price of Speed: Optimising Dark-Store Networks and Rider Assignment under Relaxed Delivery Promises in Indian Quick Commerce**

Case: Bengaluru (BBMP, 243 wards). Inputs: topic rationale in `docs/topic-proposal.md`, parameters in `config/project.yaml`, data procedure in `data/README.md`.

---

## 1. Argument in one paragraph

In January 2026, India's quick-commerce platforms dropped the "10-minute" claim under government pressure over rider safety. A Parliamentary committee then called "unrealistic speed targets" a problem without defining them. We give the definition a number:
- **Model:** we build a dark-store network for Bengaluru that guarantees a promise *T* at a *safe* rider speed *v*. We size the rider fleet, plan restocking, and estimate the probability of meeting *T* once pick/pack variability is included.
- **Answer:** we report the **marginal cost of each minute of speed**, and the speed a 10-minute promise implicitly demands from riders.
- **Literature:** the bibliometric review shows that OR has studied last-mile and meal delivery extensively, but rarely treats the promise as a policy variable or rider safety as a constraint.

## 2. Contributions (state these in the introduction)

1. A bibliometric map of OR research on on-demand and last-mile delivery from 2015 to 2026, identifying the quick-commerce and courier-welfare gap.
2. An integrated, reproducible model chain: covering location → transportation → assignment → PERT, built on public Indian data (WorldPop 2025, BBMP wards, OpenStreetMap).
3. A "price of speed" curve: stores, riders and cost against the promise time, at several safety speed caps.
4. Policy evidence on what a "realistic" delivery promise means.

## 3. Section-by-section plan (12-page budget)

| § | Section | Pages | Content | Figures / tables | Source |
|---|---|---|---|---|---|
| — | Abstract | 0.25 | Problem, data, models, headline number | — | all |
| 1 | Introduction | 1.0 | 2025–26 policy events; q-commerce scale (4,081 dark stores); gap; RQ1–RQ3; contributions | — | topic-proposal |
| 2 | Literature review | 2.25 | 2.1 Bibliometric overview; 2.2 Thematic synthesis (four clusters, below); 2.3 Gaps | F2 trend, F3 keyword network, F4 thematic map, T1 core papers | biblio/ |
| 3 | Methodology | 1.0 | 3.1 Search protocol, PRISMA; 3.2 Modelling framework (model chain diagram) | F1 PRISMA, F5 model chain | search_protocol.md |
| 4 | Case and data | 1.0 | Bengaluru study area; data sources and audit (why the Kaggle data was rejected); parameters | F6 study-area map, T2 data sources, T3 parameters | data/README.md |
| 5 | Model formulation | 2.0 | M1–M5 below; notation table | T4 notation | this doc |
| 6 | Results | 2.25 | 6.1 Price-of-speed curve; 6.2 Coverage maps; 6.3 Fleet and replenishment; 6.4 Assignment at peak; 6.5 PERT reliability; 6.6 Sensitivity | **F7 headline curve**, F8 maps, T5 results, F9 tornado, T6 PERT | results/ |
| 7 | Discussion | 1.25 | Managerial implications (platforms); policy implications (defining "realistic"); limitations; future research agenda tied to the gaps | — | |
| 8 | Conclusion | 0.25 | Answer each RQ in one sentence | — | |
| — | References | (outside limit if allowed) | Mendeley export | | |

### Literature clusters for §2.2 (expected from the keyword map; confirm against Biblioshiny output)

1. **Last-mile routing and delivery modes:** VRP variants, parcel lockers, micro-depots, crowdshipping, EVs.
2. **On-demand / meal delivery operations:** the meal delivery routing problem (Reyes et al., 2018, the anchor paper), order–courier assignment, dynamic dispatch. Reviews to cite include the MIT CTL on-demand food delivery SLR and the MSOM meal-delivery data paper.
3. **Facility location for urban fulfilment:** covering models (Church & ReVelle, 1974, the classic anchor), micro-fulfilment and dark-store location (Kewalramani & Khadilkar, 2023, arXiv:2312.11494; the Augsburg/TUM 2024 quick-commerce network planning paper; the dark-store resilience MILP).
4. **Courier welfare and gig work in OR:** expected to be thin. Its thinness *is* the gap.

> Every citation must come from the Mendeley library after screening. The anchors above are leads to verify in EBSCO, not references to paste in.

## 4. Models

Notation: *i* ∈ I are demand cells (~0.46 km grid, population *pᵢ*); *j* ∈ J are candidate dark-store cells (cells containing an OSM grocery, convenience or warehouse site); *dᵢⱼ* is the road distance (haversine × detour factor δ, calibrated with OSRM).

### M1: Covering location (strategic; LP/MILP)

Effective ride radius for promise *T* and safe speed *v*:

  r(T, v) = v · (T − t_pp − t_assign − t_handover) / 60   [km], where the fixed times are PERT means

Coverage sets: Nᵢ = { j : dᵢⱼ ≤ r(T, v) }.

- **Set covering (number of stores needed):**
  min Σⱼ yⱼ  s.t. Σ_{j∈Nᵢ} yⱼ ≥ 1 for all i with pᵢ ≥ p_min; yⱼ ∈ {0,1}
- **Maximal covering (coverage with the current fleet of *P* stores):**
  max Σᵢ pᵢ zᵢ  s.t. zᵢ ≤ Σ_{j∈Nᵢ} yⱼ; Σⱼ yⱼ = P; yⱼ, zᵢ ∈ {0,1}

Run both over the full (T, v) grid. *P* is set from public reports of Bengaluru's dark-store count (440; quickcommercemap.com, July 2026).

**First-pass finding (E1, 2026-10-06; `results/e1_price_of_speed.csv`):**
- *Set covering* alone gives a misleading picture.
- Relaxing the promise from 10 to 30 min (at 15 km/h) cuts the minimum store count from 356 to 23.
- But it *raises* peak riders from ~2.4k to ~7.5k, because rides get longer.
- So the price of speed is a **store-versus-rider trade-off**, and the headline model must be M1-cost below.

**M1-cost: coverage-constrained cost-minimising design (the main model).**
- Objective: min F·Σⱼ yⱼ + c_r · Σᵢⱼ λᵢ · cycleᵢⱼ/60 · xᵢⱼ
- Constraints: Σⱼ xᵢⱼ = 1; xᵢⱼ ≤ yⱼ; xᵢⱼ = 0 if dᵢⱼ > r(T, v); optionally Σᵢ λᵢ xᵢⱼ ≤ capⱼ.
- This is an uncapacitated (or capacitated) facility location problem with a coverage restriction.
- Variables exist only for reachable pairs, which keeps it sparse. If HiGHS struggles at the full size, aggregate demand to ~1 km cells.
- It needs **F** (store cost) and **c_r** (rider cost per hour), both sourced in `data/README.md` §5. The tornado shows how the optimum shifts across their ranges.

**Coverage gap at tight promises.** At T = 10 min, even 20 km/h leaves ~10% of the population with no candidate site in reach.
- This is partly real (sparse retail stock at the periphery) and partly OSM incompleteness.
- Add a robustness run with grid candidate sites (any populated cell is allowed) and report the difference.

### M2: Demand allocation and rider fleet sizing (follows M1)

- Allocate each demand cell to its nearest open store. This is an assignment with capacity, formulated as a transportation LP if store capacity binds.
- Peak orders per cell: λᵢ = pᵢ / 1000 × (orders per 1,000 people per peak hour) × peak multiplier.
- Riders at store *j*: Rⱼ = ⌈Σᵢ λᵢ · (2 dᵢⱼ / v · 60 + t_handover) / 60⌉ (cycle-time / Little's-law sizing).

### M3: Transportation problem (tactical replenishment)

- Sources are 2–3 mother hubs. Pick them from OSM warehouse clusters at the city edge; this is an assumption to state. Destinations are the open dark stores.
- Supply is hub capacity; demand is daily store throughput (from M2); cost is road km.
- Solve with `orpaper.models.transportation`. Report the cost and compare with Vogel's approximation.

### M4: Assignment problem (operational, at peak)

- At one representative store, take a 10-minute peak batch: *R* free riders and *n* orders.
- Cost of each rider–order pair: rider time to become free + ride time, plus a penalty if delivery would exceed *T*.
- Solve exactly with `orpaper.models.assignment` and compare against FIFO dispatch. This shows how a tight promise turns into pressure on rider speed.

### M5: PERT (fulfilment process reliability)

- Activities: order accepted → pick/pack (a, m, b) → rider assignment (a, m, b) → ride (from the distribution of *dᵢⱼ / v* over covered cells) → handover.
- Compute P(fulfilment ≤ *T*) for each (T, v).
- Headline output: the *speed riders would need* for 95% on-time delivery under a 10-minute promise.

## 5. Experiments → outputs

| ID | Varies | Fixed | Output | Feeds |
|---|---|---|---|---|
| E1 | T ∈ {10, 15, 20, 30}, v ∈ {12, 15, 20} | demand base | stores (M1-SC), riders (M2): **done, first pass** (`experiments/run_case.py`) | T5 |
| E1-cost | T, v, and the F/c_r ratio | demand base | M1-cost design: stores, riders, monthly cost, price per minute | **F7** |
| E1-grid | T, v | grid candidates instead of OSM | coverage gap attributable to OSM | robustness |
| E2 | T at v = 15 | — | coverage maps 10 vs 20 min | F8 |
| E3 | hubs × stores | E1 at T=15, v=15 | replenishment cost; LP vs VAM | T5 |
| E4 | T ∈ {10, 15, 20} | one store, peak batch | optimal vs FIFO lateness | T5 |
| E5 | T, v | PERT inputs | P(on time); speed needed for 95% | T6 |
| E6 | orders/1000 pop, peak multiplier, detour δ, pick/pack m, fixed cost, wage | E1 base | ± change in cost and stores | F9 tornado |

The **price per minute of speed** is the cost difference between consecutive promise levels divided by the minutes saved, e.g. (C₁₀ − C₁₅) / 5.

## 6. Work plan (assumes 6 weeks; adjust to the real deadline)

| Week | Bibliometric track | Modelling track | Writing |
|---|---|---|---|
| 1 | Pilot search; fix the string; run the final search, take the screenshot | `make data` done; M1 implemented and tested on a toy instance | Introduction draft |
| 2 | Screening (split pages across members); RIS export → Mendeley | M1 on the real grid; E1 first pass | Case and data section |
| 3 | Metadata verification; `.bib` → Biblioshiny; Google Scholar citations | M2 + M3; E3 | Methodology section |
| 4 | Figures; core-paper reading matrix | M4 + M5; E4, E5 | Literature review |
| 5 | — | E6 sensitivity; final figures | Results + discussion |
| 6 | Mendeley export cleanup | Reproducibility check (fresh clone) | Edit to ≤12 pages; abstract; slides |

Group: Madhav Gupta (28), Aadee Pardasani (01), Aashi Khuthia (06), Jiya Jagawat (23), Prishi Doshi (36), Aarushi Rakesh (05). Roles: search/screening, bibliometrics, modelling (M1/M2), modelling (M3–M5), data/figures, editing/presentation.

## 7. Open items needing human input

Resolved 2026-10-06 from company filings and press (see `data/README.md` §5): store and rider costs, Bengaluru daily orders (~603k), dark-store count (440), rider speed, and pick/pack times. Still open:

- **Deadline and paper template** (instructor).
- **Actual dark-store locations** for benchmarking: buy the quickcommercemap pass, geocode published address lists, or skip it (see `data/README.md` §5).
- **Primary documents:** download the Eternal and Swiggy letters and the Zepto CEO post, and add them to Mendeley.
- **Mother hub locations** for M3 (OSM warehouse-cluster assumption).
- **Target venue** for the "Publication" mark.
- **Role assignment.**

## 8. Status (2026-10-06)

- **Models built and tested:** M1-cost (`models/design.py`, checked against brute force), M2, M3, M4 (median and stressed store × staffing level), M5 PERT. All experiments run with `make experiments`; 36 tests pass.
- **Draft:** `paper/main.tex` builds to an 11-page draft with `make paper`. Introduction, methodology, data, model, results and discussion are written; numbers come from `paper/generated/numbers.tex`.
- **Headline results changed the framing:**
  - The promise mainly changes *coverage*. At T = 10, 15% of residents are out of reach of mapped retail sites.
  - With a store allowed anywhere, a 10-minute promise needs +61% stores at +8% cost per order relative to 15 minutes.
  - Rider *speed* drives cost: a 15 km/h cap costs +19% per order relative to 20 km/h.
- **Still `\todo`:** all bibliometric content (§2, the RQ1 answer, PRISMA), author names, repo link, the model-chain diagram, primary-source verification flagged in `references.bib`, and the instructor template.

## 9. Status (2026-10-06, evening)

- **Literature search:**
  - Run on OpenAlex: 7,576 → 715 → 216 records, 177 included after first-pass screening, of which 24 are flagged for a second pass.
  - Bibliometrics, core matrix, PRISMA and §2 are written from this data.
  - The search substitutes for EBSCO; a rerun on EBSCO can swap in through `make biblio-search`.
- **Policy experiments added:** fragmentation (maximal covering by store count) and the realistic-promise policy (10 min where reachable, else 15).
- **Results:** 27 of 29 MILPs proven optimal. The other two (15-minute maximal covering at 50 and 100 stores) hit the 600 s limit, and their coverage is reported as a lower bound.
- **Corrections today:**
  - PuLP labels a HiGHS time limit as "Optimal"; statuses now use `sol_status`.
  - Tied stores split demand cells fractionally, which undercounted coverage; extraction is fixed and all experiments were rerun.
- **Paper:** 11 pages in two-column layout, within the 12-page limit.
