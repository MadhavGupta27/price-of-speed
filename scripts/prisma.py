"""Screening log -> PRISMA counts (JSON) + flow diagram.

    uv run python scripts/prisma.py [--log biblio/screening_log.csv]
"""

import argparse
import json

import pandas as pd

from orpaper.biblio import plot_prisma, prisma_counts
from orpaper.config import ROOT


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default=ROOT / "biblio/screening_log.csv")
    ap.add_argument("--out-json", default=ROOT / "results/prisma_counts.json")
    ap.add_argument("--out-fig", default=ROOT / "biblio/figures/prisma_flow.png")
    a = ap.parse_args()

    log = pd.read_csv(a.log)
    if log.empty:
        raise SystemExit(f"{a.log} has no records yet - fill it during screening (PLAN.md Phase 2).")
    c = prisma_counts(log)
    with open(a.out_json, "w") as f:
        json.dump(c, f, indent=2)
    plot_prisma(c, a.out_fig)
    print(json.dumps(c, indent=2))
    if c["pending"]:
        print(f"\nWARNING: {c['pending']} records have no include/exclude decision.")


if __name__ == "__main__":
    main()
