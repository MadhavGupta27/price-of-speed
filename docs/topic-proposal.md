# Topic proposal
 

> **The Price of Speed: Optimising Dark-Store Networks and Rider Assignment under Relaxed Delivery Promises in Indian Quick Commerce**

### Why now (motivation slide)

- India's three largest quick-commerce operators ran **4,081 dark stores** by March 2026. Each store serves a radius of roughly 1.5–3 km to meet a 10–20 minute promise ([ecorpit](https://ecorpit.com/ecorpit-quick-commerce-dark-store-app-development-service-india-2026/)).
- After a nationwide gig-worker strike on 31 Dec 2025, the Union Labour Ministry intervened. In **January 2026, Blinkit, Zepto, Swiggy and Zomato dropped the "10-minute delivery" claim** over rider-safety concerns ([Outlook Business](https://www.outlookbusiness.com/corporate/quick-commerce-giants-drop-10-minute-delivery-promise-after-govt-intervention), [Onmanorama](https://www.onmanorama.com/news/business/2026/01/13/blinkit-drops-10-minute-delivery-claim.amp.html)).
- On **7 Aug 2026**, a Parliamentary Standing Committee recommended guidelines against "unrealistic speed targets" set by dispatch algorithms. It did not define what "unrealistic" means ([Outlook Business](https://www.outlookbusiness.com/amp/story/corporate/blinkit-zepto-instamart-may-face-new-rules-over-speed-algorithms)).
- **Gap:** nobody has quantified the trade-off. How many dark stores and riders, and how much cost, does each extra minute of promise buy, at a safe rider speed? An OR model can answer exactly that, and the policy debate needs the number.

### Research questions

- **RQ1 (literature):** How has OR research on on-demand / last-mile delivery evolved? Which methods dominate (location, assignment, routing), and where are the gaps for quick commerce and courier welfare?
- **RQ2 (model):** For an Indian city, how do the number of dark stores, rider fleet size and total cost change as the delivery promise relaxes from 10 to 15, 20 and 30 minutes, under a safety-capped rider speed?
- **RQ3 (managerial/policy):** What promise level and network design balance coverage, cost and rider safety? What evidence does this give for defining a "realistic" speed target?

### Model: covers all four syllabus methods

| Layer | OR method | Decision | Syllabus topic |
|---|---|---|---|
| Strategic | **Maximal covering / set covering location (MILP)** | Which candidate sites open as dark stores, so that demand lies within (promise − pick/pack time) × safe speed | LP / MILP |
| Tactical | **Transportation problem** | Replenishment flows from 1–2 mother warehouses to the open dark stores | Transportation |
| Operational | **Assignment problem** | Matching riders to orders in a peak-hour batch, minimising lateness or total travel time | Assignment |
| Process | **PERT** | Order fulfilment network (order accepted → pick → pack → rider assigned → ride) with three-point times, giving P(delivered within promise) | CPM/PERT |

**Sensitivity analysis** (explicitly in the rubric):
- Promise time (10/15/20/30 min).
- Safe rider speed cap (e.g. 15/20/25 km/h).
- Pick/pack time.
- Fleet size.
- Peak-hour demand multiplier.
- Traffic level (from the dataset).

The headline figure is a cost-vs-promise curve with a "price per minute of speed".

### Data (all public; verify each licence on download)

| Need | Source | Notes |
|---|---|---|
| Order locations, delivery times, traffic level, weather, vehicle type, in Indian cities | **Kaggle food-delivery dataset (Gaurav Malik), ~45k orders.** Fields: `Restaurant_latitude/longitude`, `Delivery_location_latitude/longitude`, `Time_taken(min)`, `Road_traffic_density`, `Weatherconditions`, `Type_of_vehicle`, `City` | Use as a proxy for demand points and **empirical rider speeds** (distance ÷ time) by traffic level. Known to be noisy (zero or negative coordinates); cleaning is part of the method. |
| Road travel times | **OpenStreetMap + OSRM** (already in `src/orpaper/data/osrm.py`) | Turns straight-line coverage into road-network coverage. |
| Population weights for demand | WorldPop / Census of India (district or ward level) | Weights the demand points. |
| Candidate dark-store sites | OSM commercial land-use or retail points, or a regular grid | Documented as an assumption. |
| SKU-level demand (optional) | Kaggle "Blinkit Sales" dataset | Only if replenishment volumes need realism. |
| Benchmark / validation (optional) | [Amazon Last Mile Routing Challenge, 9,184 real routes](https://registry.opendata.aws/amazon-last-mile-challenges) | US data; useful only to sanity-check routing parameters. |

### Literature: plenty, but thin exactly where we sit

- **Deep base:** meal delivery routing problem (Reyes et al. 2018 onward), on-demand food delivery reviews ([MIT CTL SLR](https://ctl.mit.edu/publications/demand-food-delivery-systematic-literature-review); [MSOM data paper](https://pubsonline.informs.org/doi/fpi/10.1287/msom.2022.1112)), and maximal covering location (since Church & ReVelle, 1974).
- **Adjacent bibliometric reviews to benchmark against:**
  - EVs in last-mile delivery: a 375-paper Scopus review ([UJ](https://pure.uj.ac.za/en/publications/electric-vehicles-in-last-mile-delivery-a-bibliometric-review/)).
  - Scientometric review of crowdsourced delivery ([KFUPM](https://pure.kfupm.edu.sa/en/publications/a-scientometric-analysis-of-crowdsourced-delivery-logistics/)).
  - Sustainable e-commerce logistics ([Sustainability 2022](https://ideas.repec.org/a/gam/jsusta/v14y2022i19p12247-d926559.html)).
- **Emerging q-commerce OR work (the novelty frontier):**
  - Micro-fulfilment network planning for quick commerce, a location-routing problem ([Augsburg/TUM 2024](https://portal.fis.tum.de/en/publications/winning-the-race-to-customers-with-micro-fulfillment-centers-an-a/)).
  - Dark-store resilient portfolio MILP ([TRID](https://trid.trb.org/View/2623429)).
  - Dark-store location heuristic under a delivery radius ([arXiv 2312.11494](https://arxiv.org/abs/2312.11494)).
- **Gaps we can claim:**
  1. Few studies on Indian q-commerce.
  2. Almost none treat the **promise time as a policy variable**, or rider safety as a constraint rather than a by-product.
  3. Location and assignment are rarely linked to fulfilment-time uncertainty (PERT).

### Draft search string (EBSCO; mandatory terms kept)

```
"operations" AND "research"
AND ("last-mile" OR "last mile" OR "on-demand delivery" OR "instant delivery"
     OR "quick commerce" OR "q-commerce" OR "meal delivery" OR "dark store"
     OR "micro-fulfil*" OR "crowdshipping")
AND ("facility location" OR "covering" OR "assignment" OR "vehicle routing"
     OR "integer programming" OR "linear programming")
```

Suggested years: 2015–2026. Run a pilot search first; if the count is over ~1,500, drop `crowdshipping` and `last mile` (the space variant); if it is under ~150, drop the method clause.

### Why this scores well on the rubric

| Criterion | How this topic earns it |
|---|---|
| Novelty & intro (paper 2) | 2026 policy event, with no OR quantification of it yet |
| Lit review & methodology (2 / 15 pts) | Large on-demand delivery corpus; clean thematic clusters (routing, location, crowdshipping, sustainability) |
| Model formulation (20 pts) | Four connected classical models, each textbook-checkable |
| Data & reproducibility (15 pts) | Fully public data; the scaffold already has OSRM, a sensitivity runner, and the transportation/assignment/PERT models |
| Results & sensitivity (20 pts) | The promise-time sweep *is* the result; easy, intuitive charts |
| Discussion / future agenda (2) | Gig-worker welfare, EV fleets, dynamic dispatch, regulation design |
| Publication (2) | Fits Indian management/OR outlets (e.g. *OPSEARCH*, *IIMB Management Review*) and sustainability/transport journals |
| Presentation / Q&A (20 pts) | Relatable (everyone uses Blinkit/Zepto); one memorable chart: the "price per minute" |

### Risks and mitigations

- **No real dark-store locations or order data from the platforms.** Mitigation: use the Kaggle food-delivery orders as a demand proxy and state the assumption. Restaurant and dark-store demand patterns are both dense urban last-mile flows.
- **Kaggle data noise.** Mitigation: filter impossible coordinates, then document the counts dropped in `data/README.md`.
- **Scope creep (four models).** Mitigation: location + sensitivity is the core. Transportation, assignment and PERT are small add-ons, each about one page.

---

## Alternatives (if the group prefers)

**B. Ambulance (108) location in an Indian city: maximal covering + assignment.**
- *Data:* India Urban Data Exchange (IUDX) publishes ambulance GPS/route data for Bengaluru, Chandigarh and Vadodara ([IUDX ambulance stories](https://ambulancestories.iudx.org.in/bengaluru/)). Access requires registration, so check this first.
- *Literature:* deep (EMS location since the 1970s). India-specific studies exist ([Delhi TRB 2020](https://nitc.trec.pdx.edu/sites/default/files/TRB%202020%20-%20PSU%20-%20Ambulance%20Location%20Optimization%20Incorporating%20O-D%20Travel%20Time%20Variability-%20A%20Case%20Study%20of%20Delhi.pdf), showing a 20% improvement).
- *Assessment:* less novel, high social impact.

**C. Flood relief logistics in Assam: PERT/CPM for response mobilisation + transportation model for relief distribution** (guideline topic #9).
- *Literature:* rich, with existing bibliometric reviews ([894-study HL bibliometric](https://acta.sze.hu/index.php/acta/article/view/647)).
- *Data:* mostly synthetic. District warehouse and demand data are hard to get, which weakens the data/reproducibility marks.
