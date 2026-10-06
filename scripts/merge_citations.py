"""Attach Google Scholar citation counts to the cleaned Biblioshiny export and
produce a core-paper candidate shortlist (PLAN.md Phase 3, Step 14).

Get citations in bulk with Harzing's Publish or Perish (Google Scholar source),
export as CSV, then:

    uv run python scripts/merge_citations.py \
        --records biblio/exports/biblioshiny_export.xlsx \
        --pop biblio/exports/publish_or_perish.csv \
        --retrieved 2026-10-20
"""

import argparse

import pandas as pd

from orpaper.biblio import merge_citations, shortlist_core
from orpaper.config import ROOT, load_config


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--records", default=ROOT / "biblio/exports/biblioshiny_export.xlsx")
    ap.add_argument("--pop", default=ROOT / "biblio/exports/publish_or_perish.csv")
    ap.add_argument("--retrieved", required=True, help="date citations were pulled (YYYY-MM-DD)")
    ap.add_argument("--out", default=ROOT / "biblio/exports/records_with_gs.xlsx")
    ap.add_argument("--shortlist", default=ROOT / "biblio/core_candidates.csv")
    a = ap.parse_args()

    merged = merge_citations(pd.read_excel(a.records), pd.read_csv(a.pop), a.retrieved)
    merged.to_excel(a.out, index=False)
    unmatched = int((merged["GS_match"] == "UNMATCHED").sum())
    print(f"Wrote {a.out}: {len(merged)} records, {unmatched} unmatched (look these up by hand).")

    shortlist_core(merged, n=cfg["bibliometrix"]["core_papers_n"]).to_csv(a.shortlist, index=False)
    print(f"Wrote {a.shortlist}: candidates ranked by citations/year; fill 'selected' by hand.")


if __name__ == "__main__":
    main()
