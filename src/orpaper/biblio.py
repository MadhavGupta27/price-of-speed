"""Bibliographic dataset helpers: screening/PRISMA counts, citation merge, core-paper shortlist.

Inputs are produced by humans (screening log) or by Biblioshiny/Publish or Perish
exports; this module only does the bookkeeping so the numbers in the paper are
reproducible from files in biblio/.
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

SCREENING_COLUMNS = [
    "record_id", "source_db", "search_page", "title", "authors", "year", "journal",
    "doi", "document_type", "duplicate", "decision", "exclusion_reason", "screener", "notes",
]


def normalise_title(t) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(t).lower()).strip()


def normalise_doi(d) -> str:
    d = str(d or "").strip().lower()
    d = re.sub(r"^https?://(dx\.)?doi\.org/", "", d)
    return "" if d in ("", "nan", "none") else d


def _yes(s: pd.Series) -> pd.Series:
    return s.astype(str).str.strip().str.lower().isin(["yes", "y", "true", "1"])


def prisma_counts(log: pd.DataFrame) -> dict:
    """Counts for the screening flow from biblio/screening_log.csv."""
    dup = _yes(log["duplicate"])
    screened = log[~dup]
    decision = screened["decision"].astype(str).str.strip().str.lower()
    excluded = screened[decision == "exclude"]
    pending = int((~decision.isin(["include", "exclude"])).sum())
    return {
        "identified": len(log),
        "identified_by_db": log["source_db"].value_counts().to_dict(),
        "duplicates_removed": int(dup.sum()),
        "screened": len(screened),
        "excluded": len(excluded),
        "excluded_by_reason": excluded["exclusion_reason"].fillna("unspecified")
                              .value_counts().to_dict(),
        "excluded_by_doc_type": excluded["document_type"].fillna("unspecified")
                                .value_counts().to_dict(),
        "included": int((decision == "include").sum()),
        "pending": pending,
    }


def plot_prisma(c: dict, out: str | Path):
    """Simple vertical PRISMA-style flow diagram."""
    reasons = "\n".join(f"{k}: {v}" for k, v in c["excluded_by_reason"].items()) or "-"
    dbs = ", ".join(f"{k} n={v}" for k, v in c["identified_by_db"].items())
    main = [
        f"Records identified\n({dbs})\nn = {c['identified']}",
        f"Records after duplicates removed\nn = {c['screened']}",
        f"Records screened\nn = {c['screened']}",
        f"Studies included in bibliometric analysis\nn = {c['included']}",
    ]
    side = {1: f"Duplicates removed\nn = {c['duplicates_removed']}",
            2: f"Records excluded\nn = {c['excluded']}\n{reasons}"}

    fig, ax = plt.subplots(figsize=(8, 8))
    ax.axis("off")
    ys = [0.88, 0.64, 0.40, 0.14]
    box = dict(boxstyle="round,pad=0.6", fc="white", ec="black")
    for i, (y, text) in enumerate(zip(ys, main)):
        ax.text(0.32, y, text, ha="center", va="center", fontsize=10, bbox=box)
        if i < len(ys) - 1:
            ax.annotate("", xy=(0.32, ys[i + 1] + 0.07), xytext=(0.32, y - 0.07),
                        arrowprops=dict(arrowstyle="->"))
        if i in side:
            ax.text(0.80, y, side[i], ha="center", va="center", fontsize=9, bbox=box)
            ax.annotate("", xy=(0.64, y), xytext=(0.56, y), arrowprops=dict(arrowstyle="->"))
    if c["pending"]:
        ax.text(0.5, 0.01, f"WARNING: {c['pending']} records not yet screened",
                ha="center", color="crimson")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200, bbox_inches="tight")
    plt.close(fig)


def merge_citations(records: pd.DataFrame, pop: pd.DataFrame, retrieved: str) -> pd.DataFrame:
    """Attach Google Scholar citation counts to the Biblioshiny export.

    `records`: Biblioshiny Excel export (WoS field tags: TI title, DI DOI, PY year).
    `pop`: Publish or Perish CSV export (columns Cites, Title, DOI).
    Matches on DOI first, then normalised title. Unmatched rows get GS_TC = NA
    and must be looked up by hand.
    """
    pop = pop.copy()
    pop["_doi"] = pop.get("DOI", pd.Series(dtype=str)).map(normalise_doi)
    pop["_ti"] = pop["Title"].map(normalise_title)
    by_doi = pop[pop["_doi"] != ""].drop_duplicates("_doi").set_index("_doi")["Cites"]
    by_ti = pop.drop_duplicates("_ti").set_index("_ti")["Cites"]

    out = records.copy()
    doi = out.get("DI", pd.Series("", index=out.index)).map(normalise_doi)
    ti = out["TI"].map(normalise_title)
    gs = doi.map(by_doi)
    gs = gs.where(gs.notna(), ti.map(by_ti))
    out["GS_TC"] = gs
    out["GS_match"] = (doi.map(by_doi).notna().map({True: "doi", False: None})
                       .fillna(ti.map(by_ti).notna().map({True: "title", False: "UNMATCHED"})))
    out["GS_retrieved"] = retrieved
    return out


def shortlist_core(records: pd.DataFrame, n: int = 20, current_year: int | None = None,
                   cites_col: str = "GS_TC") -> pd.DataFrame:
    """Rank candidates by citations per year (fairer to recent papers).

    Output is a *candidate* list: the group must still confirm relevance by
    reading abstracts and fill the `selected` column (PLAN.md Phase 3).
    """
    df = records.copy()
    year = pd.to_numeric(df["PY"], errors="coerce")
    current_year = current_year or int(year.max())
    cites = pd.to_numeric(df[cites_col], errors="coerce").fillna(0)
    df["cites_per_year"] = cites / (current_year - year + 1).clip(lower=1)
    df = df.sort_values("cites_per_year", ascending=False)
    cols = [c for c in ["TI", "AU", "PY", "SO", "DI", cites_col, "cites_per_year"] if c in df]
    out = df[cols].head(n * 2).reset_index(drop=True)
    out["selected"] = ""  # TODO(human): mark yes/no after reading abstracts
    out["reason"] = ""
    return out
