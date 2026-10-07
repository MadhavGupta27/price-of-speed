"""Bibliographic search on OpenAlex replicating the EBSCO protocol (PLAN.md Phase 2).

    uv run python scripts/openalex_search.py

Why OpenAlex: EBSCO requires an institutional login. OpenAlex is an open index
with abstracts, author keywords/topics, citation counts and reference lists, so
the same Boolean protocol can be run reproducibly. Re-run on EBSCO and swap the
records in if the course requires EBSCO data specifically.

Procedure (counts recorded in results/search_log.json):
  1. Server side, one query per topic term (OpenAlex throttles >5 Boolean operators):
     title_and_abstract.search:"<term>" with filters type:article, language:en,
     publication_year:2015-2026, primary_location.source.type:journal.
  2. Union by OpenAlex ID -> records identified.
  3. Locally: method clause on title+abstract; mandatory "operations" AND "research"
     on title + abstract + journal name + keywords (approximates EBSCO default fields).
  4. Duplicates removed by DOI, then normalised title.
Outputs: biblio/raw/openalex_*.jsonl, biblio/openalex_records.csv, results/search_log.json
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import pandas as pd
import requests

from orpaper.config import ROOT, load_config

API = "https://api.openalex.org/works"


def load_dotenv(path=ROOT / ".env"):
    """Minimal .env reader (KEY=VALUE lines) so the API key never lives in code or git."""
    if path.exists():
        for line in path.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip().removeprefix("export ").strip(), v.strip().strip("'\""))


load_dotenv()
RAW = ROOT / "biblio/raw"

TOPIC_TERMS = ["last-mile", "last mile", "on-demand delivery", "instant delivery", "quick commerce",
               "q-commerce", "meal delivery", "dark store", "micro-fulfillment", "micro-fulfilment",
               "crowdshipping"]
METHOD_TERMS = ["facility location", "covering", "assignment", "vehicle routing",
                "integer programming", "linear programming"]
FIELDS = ("id,doi,title,display_name,publication_year,type,language,primary_location,authorships,"
          "abstract_inverted_index,keywords,topics,cited_by_count,referenced_works,biblio")


def abstract_text(inv):
    if not inv:
        return ""
    pos = sorted((p, w) for w, ps in inv.items() for p in ps)
    return " ".join(w for _, w in pos)


def term_regex(term):
    # loose stemming: allow plural/-ing/-ed suffixes and hyphen/space variants, like OpenAlex stemming
    t = re.escape(term.lower()).replace(r"\-", r"[-\s]?").replace(r"\ ", r"[-\s]?")
    return re.compile(r"\b" + t + r"\w*", re.I)


def fetch_term(term, years):
    flt = (f"type:article,language:en,publication_year:{years[0]}-{years[1]},"
           f"primary_location.source.type:journal,title_and_abstract.search:\"{term}\"")
    out, cursor = [], "*"
    while cursor:
        for attempt in range(8):
            params = {"filter": flt, "per-page": 200, "cursor": cursor, "select": FIELDS}
            if os.environ.get("OPENALEX_API_KEY"):  # free key: https://help.openalex.org/api/authentication/
                params["api_key"] = os.environ["OPENALEX_API_KEY"]
            r = requests.get(API, params=params, timeout=120)
            body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
            if r.status_code == 200 and "results" in body:
                break
            print(f"  retry {attempt + 1} ({r.status_code}: {str(body)[:120]})", flush=True)
            time.sleep(10 * (attempt + 1))
        else:
            raise RuntimeError(f"OpenAlex failed for {term!r}")
        out += body["results"]
        cursor = body["meta"].get("next_cursor")
        time.sleep(0.15)
    return out


def flatten(w):
    src = ((w.get("primary_location") or {}).get("source") or {})
    auths = w.get("authorships") or []
    return {
        "openalex_id": w["id"].rsplit("/", 1)[1],
        "doi": (w.get("doi") or "").replace("https://doi.org/", "").lower(),
        "title": w.get("display_name") or "",
        "year": w.get("publication_year"),
        "journal": src.get("display_name") or "",
        "authors": "; ".join(a["author"]["display_name"] for a in auths if a.get("author")),
        "countries": "; ".join(sorted({c for a in auths for c in (a.get("countries") or [])})),
        "institutions": "; ".join(sorted({i["display_name"] for a in auths for i in (a.get("institutions") or [])})),
        "abstract": abstract_text(w.get("abstract_inverted_index")),
        "keywords": "; ".join(k["display_name"] for k in (w.get("keywords") or [])),
        "topics": "; ".join(t["display_name"] for t in (w.get("topics") or [])[:3]),
        "cited_by": w.get("cited_by_count", 0),
        "n_refs": len(w.get("referenced_works") or []),
        "referenced_works": " ".join(r.rsplit("/", 1)[1] for r in (w.get("referenced_works") or [])),
        "volume": (w.get("biblio") or {}).get("volume"),
        "issue": (w.get("biblio") or {}).get("issue"),
        "first_page": (w.get("biblio") or {}).get("first_page"),
        "last_page": (w.get("biblio") or {}).get("last_page"),
    }


def main():
    cfg = load_config()["search"]
    years = (cfg["year_start"], cfg["year_end"])
    RAW.mkdir(parents=True, exist_ok=True)
    log = {"run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "database": "OpenAlex",
           "filters": f"type:article, language:en, years {years[0]}-{years[1]}, source type journal",
           "per_term_hits": {}}

    works = {}
    for term in TOPIC_TERMS:
        path = RAW / f"openalex_{re.sub(r'[^a-z]+', '_', term)}.jsonl"
        if path.exists():  # cached from an earlier run
            res = [json.loads(line) for line in open(path)]
        else:
            res = fetch_term(term, years)
            with open(path, "w") as f:
                for w in res:
                    f.write(json.dumps(w) + "\n")
        log["per_term_hits"][term] = len(res)
        for w in res:
            works[w["id"]] = w
        print(f"{term!r}: {len(res)}", flush=True)

    df = pd.DataFrame([flatten(w) for w in works.values()])
    log["identified_union"] = len(df)

    text = (df["title"] + " " + df["abstract"]).str.lower()
    method = pd.concat([text.str.contains(term_regex(t)) for t in METHOD_TERMS], axis=1).any(axis=1)
    wide = (text + " " + df["journal"].str.lower() + " " + df["keywords"].str.lower()
            + " " + df["topics"].str.lower())
    mandatory = wide.str.contains(r"\boperation\w*", regex=True) & wide.str.contains(r"\bresearch\w*", regex=True)
    df["match_method"], df["match_mandatory"] = method, mandatory
    log["after_method_clause"] = int(method.sum())
    log["after_mandatory_terms"] = int((method & mandatory).sum())
    df = df[method & mandatory].copy()

    # duplicates (same DOI, or same normalised title + year)
    norm = df["title"].str.lower().str.replace(r"[^a-z0-9]+", " ", regex=True).str.strip()
    dup = (df["doi"].ne("") & df["doi"].duplicated()) | pd.Series(list(zip(norm, df["year"]))).duplicated().to_numpy()
    df["duplicate"] = dup
    log["duplicates"] = int(dup.sum())
    log["records_for_screening"] = int((~dup).sum())
    log["no_abstract"] = int((df["abstract"].str.len() == 0).sum())

    df.to_csv(ROOT / "biblio/openalex_records.csv", index=False)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/search_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
