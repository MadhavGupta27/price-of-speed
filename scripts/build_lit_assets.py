"""Literature-review assets for the paper from the screened OpenAlex records.

    uv run python scripts/build_lit_assets.py

Writes
  biblio/core_papers_matrix.csv       coding matrix of the core papers (PLAN.md Phase 4)
  paper/lit.bib                       BibTeX for core papers + most co-cited references (from OpenAlex metadata)
  paper/generated/lit_keys.json       openalex id -> citation key
  paper/generated/tab_core.tex        core-paper table
  paper/generated/biblio_numbers.tex  bibliometric macros
"""

import json
import re
import unicodedata

import pandas as pd

from orpaper.config import ROOT

GEN = ROOT / "paper/generated"
RES = ROOT / "results"

# Core set: highest citations per year + papers closest to quick commerce / on-demand / promise / fairness.
CORE = ["W2767877925", "W2742261706", "W2943166133", "W3130612522", "W2947601823", "W3174853550",
        "W4321014257", "W4407792646", "W4221162600", "W3129292331", "W4408619551", "W4416338006",
        "W7138846739", "W4411078849", "W7162459885", "W4407356519"]
N_COCITED = 8

# Coding for core papers whose abstracts were missing in OpenAlex; coded from the abstracts
# retrieved via Semantic Scholar / Crossref by DOI (2026-10-07).
CORE_OVERRIDES = {
    "W2742261706": dict(problem="two-echelon VRP with pickup-facility delivery options",
                        method="hybrid multi-population genetic algorithm", data="benchmark + real instance",
                        finding="Hybrid GA solves a large instance family including a real-world e-commerce case."),
    "W2943166133": dict(problem="VRP with drones and en route launch/retrieval",
                        method="MILP with valid inequalities; VNS/tabu search", data="synthetic/benchmark",
                        finding="En route operations raise drone utilisation and improve makespan."),
    "W3130612522": dict(problem="VRPTW with vans carrying delivery robots",
                        method="ALNS heuristic", data="synthetic/benchmark",
                        finding="Delivery robots are a viable alternative last-mile service under time windows."),
    "W2947601823": dict(problem="online drone fleet dispatch for on-demand meal delivery",
                        method="MIP with rolling-horizon progressive algorithm", data="simulation",
                        finding="Continuous-space MIP supports dynamic dispatch with arbitrary pickup/delivery points."),
}


def ascii_slug(s):
    for a, b in (("ø", "o"), ("Ø", "O"), ("æ", "ae"), ("ß", "ss"), ("ł", "l"), ("đ", "d")):
        s = s.replace(a, b)
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower())


def tex_escape(s):
    s = str(s)
    for a, b in (("&", r"\&"), ("%", r"\%"), ("_", r"\_"), ("#", r"\#")):
        s = s.replace(a, b)
    return s


def make_key(surname, year, used):
    base = f"{ascii_slug(surname) or 'anon'}{year}"
    key, k = base, 0
    while key in used:
        k += 1
        key = base + "abcdefghij"[k - 1]
    used.add(key)
    return key


def bib_entry(key, authors, title, journal, year, volume="", number="", pages="", doi=""):
    fields = {"author": " and ".join(authors), "title": "{" + tex_escape(title) + "}",
              "journal": tex_escape(journal), "year": year, "volume": volume, "number": number,
              "pages": pages, "doi": doi}
    body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if str(v) not in ("", "nan", "None"))
    return f"@article{{{key},\n{body}\n}}\n"


# Topic indicators counted over title + abstract + keywords of included records (gap evidence).
GAP_PATTERNS = {
    "quick_commerce_or_dark_store": r"quick[- ]commerce|q-commerce|dark[- ]store|micro[- ]fulfil",
    "on_demand_meal_instant": r"on-demand|meal deliver|food deliver|instant deliver|grocery",
    "india": r"\bindia|bengaluru|bangalore|delhi|mumbai",
    "courier_welfare_safety": r"courier (?:welfare|safety|wellbeing|well-being|fatigue|workload|fairness)|driver (?:welfare|safety|fatigue|workload|fairness)|rider (?:safety|welfare)|fair(?:ness)? (?:for|among|to) (?:couriers|drivers|riders)|gig work|road safety|accident",
    "promise_as_decision": r"delivery (?:time )?promise|promised (?:delivery )?time|delivery (?:time )?guarantee|service level (?:design|choice)|delivery speed",
    "location_models": r"facility location|location[- ]routing|covering|p-median|hub location|micro-hub|microhub|locker location",
    "assignment_matching": r"assignment|matching|dispatch",
    "drones_robots": r"drone|uav|unmanned aerial|robot",
    "review": r"\breview\b|survey|bibliometric",
}


def gap_indicators(inc):
    txt = (inc["title"].fillna("") + " " + inc["abstract"].fillna("") + " " + inc["keywords"].fillna("")).str.lower()
    res = {k: int(txt.str.contains(v, regex=True).sum()) for k, v in GAP_PATTERNS.items()}
    res["included"] = len(inc)
    (RES / "gap_indicators.json").write_text(json.dumps(res, indent=1))
    return res


def main():
    GEN.mkdir(parents=True, exist_ok=True)
    m = pd.read_csv(ROOT / "biblio/screened_records.csv")
    inc = m[m["decision"] == "include"].copy()
    gap_indicators(inc)
    used, keys, bib = set(), {}, []

    core = inc.set_index("openalex_id").loc[CORE].reset_index()
    for pid, o in CORE_OVERRIDES.items():
        for k, v in o.items():
            core.loc[core["openalex_id"] == pid, k] = v
    for r in core.itertuples():
        authors = [a for a in str(r.authors).split("; ") if a]
        key = make_key(authors[0].split()[-1] if authors else "anon", int(r.year), used)
        keys[r.openalex_id] = key
        pages = f"{int(r.first_page)}--{int(r.last_page)}" if str(r.first_page).isdigit() and str(r.last_page).isdigit() else ""
        bib.append(bib_entry(key, authors, r.title, r.journal, int(r.year), r.volume, r.issue, pages, r.doi))

    core_out = pd.DataFrame({
        "paper_id": core["openalex_id"], "citation_key": core["openalex_id"].map(keys), "title": core["title"],
        "year": core["year"], "journal": core["journal"], "gs_citations": "", "openalex_citations": core["cited_by"],
        "problem_type": core["problem"], "or_method": core["method"], "data_type": core["data"],
        "region": core["region"].fillna(""), "key_findings": core["finding"],
        "reviewer": "LLM-assisted coding from abstract; verify against full text"})
    core_out.to_csv(ROOT / "biblio/core_papers_matrix.csv", index=False)

    # most co-cited references (local citations within the included set)
    refs = {}
    for line in open(ROOT / "biblio/raw/openalex_references.jsonl"):
        w = json.loads(line)
        refs[w["id"].rsplit("/", 1)[1]] = w
    counts = inc["referenced_works"].fillna("").str.split().explode().value_counts()
    cocited = []
    for rid, n in counts.head(N_COCITED).items():
        w = refs.get(rid)
        if not w:
            continue
        authors = [a["author"]["display_name"] for a in (w.get("authorships") or [])]
        src = ((w.get("primary_location") or {}).get("source") or {}).get("display_name", "")
        key = make_key(authors[0].split()[-1] if authors else "anon", w["publication_year"], used)
        keys[rid] = key
        bib.append(bib_entry(key, authors, w["display_name"], src, w["publication_year"],
                             doi=(w.get("doi") or "").replace("https://doi.org/", "")))
        cocited.append({"key": key, "local_citations": int(n), "title": w["display_name"], "year": w["publication_year"]})
    pd.DataFrame(cocited).to_csv(RES / "cocited_core.csv", index=False)

    (ROOT / "paper/lit.bib").write_text("% Generated by scripts/build_lit_assets.py from OpenAlex metadata\n\n" + "\n".join(bib))
    (GEN / "lit_keys.json").write_text(json.dumps(keys, indent=1))

    # core table
    lines = [r"\begin{tabular}{p{0.18\linewidth}p{0.28\linewidth}p{0.28\linewidth}p{0.12\linewidth}}", r"\toprule",
             r"Study & Problem & Method & Data \\", r"\midrule"]
    for r in core_out.sort_values("year").itertuples():
        lines.append(f"\\citet{{{r.citation_key}}} & {tex_escape(r.problem_type)} & {tex_escape(r.or_method)} & {tex_escape(r.data_type).replace('/', '/ ')} \\\\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    (GEN / "tab_core.tex").write_text("\n".join(lines) + "\n")

    # bibliometric macros
    sl = json.loads((RES / "search_log.json").read_text())
    gap = json.loads((RES / "gap_indicators.json").read_text())
    excl = m[m["decision"] == "exclude"]["exclusion_reason"].value_counts()
    srcs = pd.read_csv(RES / "top_sources.csv")
    yr = pd.read_csv(RES / "annual_production.csv").set_index("year")["n"]
    growth = float((RES / "annual_growth_rate.txt").read_text())
    kw = pd.read_csv(RES / "top_keywords.csv")
    mac = lambda n, v: f"\\newcommand{{\\{n}}}{{{v}}}\n"
    out = [mac("BibIdentified", f"{sl['identified_union']:,}"), mac("BibAfterMethod", f"{sl['after_method_clause']:,}"),
           mac("BibScreened", sl["records_for_screening"]), mac("BibIncluded", gap["included"]),
           mac("BibExcluded", int(excl.sum())), mac("BibExclScope", int(excl.get("out_of_scope", 0))),
           mac("BibExclNoOR", int(excl.get("no_or_method", 0))), mac("BibExclIntro", int(excl.get("introduction", 0))),
           mac("BibSearchDate", sl["run_utc"][:10]),
           mac("BibGrowthPct", f"{100 * growth:.1f}"),
           mac("BibSinceTwentyOnePct", f"{100 * yr[yr.index >= 2021].sum() / yr.sum():.0f}"),
           mac("BibYearsTwentyFive", int(yr.get(2025, 0))),
           mac("BibTopJournal", tex_escape(srcs.iloc[0]["item"].title().replace("Of", "of"))),
           mac("BibTopJournalN", int(srcs.iloc[0]["n"])),
           mac("BibSecondJournal", tex_escape(srcs.iloc[1]["item"].title())),
           mac("BibSecondJournalN", int(srcs.iloc[1]["n"])),
           mac("BibDrones", gap["drones_robots"]), mac("BibAssign", gap["assignment_matching"]),
           mac("BibLocation", gap["location_models"]), mac("BibOnDemand", gap["on_demand_meal_instant"]),
           mac("BibQComm", gap["quick_commerce_or_dark_store"]), mac("BibIndia", gap["india"]),
           mac("BibWelfare", gap["courier_welfare_safety"]), mac("BibPromise", gap["promise_as_decision"]),
           mac("BibReviews", gap["review"]),
           mac("BibMILPKw", int(kw[kw["item"].str.contains("MIXED")]["n"].sum())),
           mac("BibALNSKw", int(kw[kw["item"].str.contains("LARGE NEIGHBORHOOD")]["n"].sum()))]
    (GEN / "biblio_numbers.tex").write_text("% Generated by scripts/build_lit_assets.py -- do not edit\n" + "".join(out))
    print(json.dumps({"core": len(core_out), "cocited": cocited}, indent=1))


if __name__ == "__main__":
    main()
