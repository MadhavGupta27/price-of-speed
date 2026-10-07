"""Convert included OpenAlex records into the files the bibliometric pipeline expects.

    uv run python scripts/openalex_to_bibliometrix.py

Outputs
  biblio/exports/biblioshiny_export.xlsx   bibliometrix data frame (WoS field tags), read by 02_analysis.R
  biblio/exports/included_records.ris      import into Mendeley (Step 9 deliverable)
  biblio/exports/included_records.bib      BibTeX of included records (keys = openalex ids)
  biblio/raw/openalex_references.jsonl     metadata of cited references (cache)

CR (cited references) are rebuilt as "AUTHOR I, YEAR, SOURCE" strings from OpenAlex
referenced_works so co-citation analysis works; TC is the OpenAlex citation count
(replace with Google Scholar counts via scripts/merge_citations.py if required).
"""

import json
import re
import time

import pandas as pd
import pycountry
import requests

from openalex_search import API, load_dotenv  # noqa: F401  (load_dotenv runs on import)
from orpaper.config import ROOT

import os

REF_CACHE = ROOT / "biblio/raw/openalex_references.jsonl"
OUT = ROOT / "biblio/exports"


def get(params):
    if os.environ.get("OPENALEX_API_KEY"):
        params["api_key"] = os.environ["OPENALEX_API_KEY"]
    for attempt in range(6):
        r = requests.get(API, params=params, timeout=120)
        if r.status_code == 200:
            return r.json()
        time.sleep(5 * (attempt + 1))
    r.raise_for_status()


def fetch_references(ids):
    have = {}
    if REF_CACHE.exists():
        have = {json.loads(l)["id"].rsplit("/", 1)[1]: json.loads(l) for l in open(REF_CACHE)}
    todo = [i for i in ids if i not in have]
    with open(REF_CACHE, "a") as f:
        for k in range(0, len(todo), 100):
            chunk = todo[k:k + 100]
            body = get({"filter": "openalex:" + "|".join(chunk), "per-page": 100,
                        "select": "id,display_name,publication_year,authorships,primary_location,doi"})
            for w in body["results"]:
                have[w["id"].rsplit("/", 1)[1]] = w
                f.write(json.dumps(w) + "\n")
            time.sleep(0.1)
    return have


def short_author(name):
    parts = (name or "").replace(".", "").split()
    if not parts:
        return "ANONYMOUS"
    return (parts[-1] + " " + "".join(p[0] for p in parts[:-1])).upper().strip()


def cr_string(w):
    auths = w.get("authorships") or []
    first = short_author(auths[0]["author"]["display_name"]) if auths else "ANONYMOUS"
    src = (((w.get("primary_location") or {}).get("source")) or {}).get("display_name") or "UNKNOWN SOURCE"
    s = f"{first}, {w.get('publication_year')}, {src.upper()}"
    return re.sub(r"[;]", ",", s)


def country_name(code):
    c = pycountry.countries.get(alpha_2=code)
    return (c.name if c else code).upper()


def main():
    m = pd.read_csv(ROOT / "biblio/screened_records.csv")
    inc = m[m["decision"] == "include"].copy().reset_index(drop=True)
    for c in ("abstract", "keywords", "topics", "referenced_works", "countries", "authors", "doi"):
        inc[c] = inc[c].fillna("")

    ref_ids = sorted({r for refs in inc["referenced_works"] for r in refs.split()})
    refs = fetch_references(ref_ids)
    print(f"references: {len(ref_ids)} unique, {len(refs)} with metadata")

    M = pd.DataFrame({
        "AU": inc["authors"].map(lambda a: ";".join(short_author(x) for x in a.split("; ") if x)),
        "AF": inc["authors"].str.upper().str.replace("; ", ";"),
        "TI": inc["title"].str.upper(),
        "SO": inc["journal"].str.upper(),
        "PY": inc["year"].astype(int),
        "DT": "ARTICLE",
        "DE": inc["keywords"].str.upper().str.replace("; ", ";"),
        "ID": inc["topics"].str.upper().str.replace("; ", ";"),
        "AB": inc["abstract"],
        "TC": inc["cited_by"].astype(int),
        "DI": inc["doi"],
        "CR": inc["referenced_works"].map(lambda rs: ";".join(cr_string(refs[r]) for r in rs.split() if r in refs)),
        "AU_CO": inc["countries"].map(lambda cs: ";".join(country_name(c) for c in cs.split("; ") if c)),
        "C1": inc["institutions"].fillna("").str.upper().str.replace("; ", ";"),
        "DB": "OPENALEX",
        "UT": inc["openalex_id"],
        "VL": inc["volume"].fillna("").astype(str), "PP": inc["first_page"].fillna("").astype(str),
    })
    M["SR"] = M["AU"].str.split(";").str[0] + ", " + M["PY"].astype(str) + ", " + M["SO"]
    OUT.mkdir(parents=True, exist_ok=True)
    M.to_excel(OUT / "biblioshiny_export.xlsx", index=False)

    # RIS + BibTeX for Mendeley / LaTeX
    ris, bib = [], []
    for r in inc.itertuples():
        ris += ["TY  - JOUR"] + [f"AU  - {a}" for a in r.authors.split("; ") if a] + [
            f"TI  - {r.title}", f"JO  - {r.journal}", f"PY  - {int(r.year)}",
            f"DO  - {r.doi}" if r.doi else "", f"AB  - {r.abstract}" if r.abstract else "",
            f"KW  - {r.keywords}" if r.keywords else "", f"UR  - https://openalex.org/{r.openalex_id}", "ER  - ", ""]
        authors = " and ".join(r.authors.split("; "))
        pages = f"{r.first_page}--{r.last_page}" if pd.notna(r.first_page) and pd.notna(r.last_page) else ""
        fields = {"author": authors, "title": "{" + r.title + "}", "journal": r.journal, "year": int(r.year),
                  "volume": "" if pd.isna(r.volume) else r.volume, "number": "" if pd.isna(r.issue) else r.issue,
                  "pages": pages, "doi": r.doi}
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields.items() if str(v) not in ("", "nan"))
        bib.append(f"@article{{{r.openalex_id},\n{body}\n}}\n")
    (OUT / "included_records.ris").write_text("\n".join(x for x in ris if x is not None))
    (OUT / "included_records.bib").write_text("\n".join(bib))
    print(f"Wrote {len(M)} records -> {OUT}")


if __name__ == "__main__":
    main()
