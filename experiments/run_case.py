"""E1: price-of-speed sweep on the Bengaluru instance (docs/paper-plan.md §4-5).

For every (promise T, safe speed v):
  M1  set covering -> minimum dark stores covering every reachable demand cell
  M2  nearest-store allocation + cycle-time rider sizing at peak
Demand: lambda_i = pop_i / sum(pop) * Bengaluru daily orders * peak-hour share.
Monthly cost = stores * F + daily orders * mean cycle (h) / utilisation * rider cost/h * 30.
Base case = middle value of each config range.

    uv run python experiments/run_case.py
"""

import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from orpaper.config import ROOT, load_config
from orpaper.data.osrm import haversine_matrix
from orpaper.models.covering import coverage_sets, nearest_open, ride_radius_km, set_covering
from orpaper.models.cpm_pert import pert_estimates

PROC = ROOT / "data/processed"


def load_instance():
    D = pd.read_csv(PROC / "blr_demand_cells.csv")
    C = pd.read_csv(PROC / "blr_candidates.csv")
    detour = json.loads((PROC / "detour_calibration.json").read_text())["detour_median"]
    pts = np.vstack([D[["lat", "lon"]].to_numpy(), C[["lat", "lon"]].to_numpy()])
    dist = haversine_matrix(pts)[: len(D), len(D):] * detour
    return D, C, dist, detour


def fixed_minutes(case):
    acts = {k: {**case[k], "pred": []} for k in ("pick_pack_min", "rider_assign_min", "handover_min")}
    te, _ = pert_estimates(acts)
    return sum(te.values()), te


def riders_needed(dist_to_store, store_of_cell, orders_per_hour, speed_kmh, handover_min):
    """Cycle-time sizing per store: riders = ceil(sum_i lambda_i * cycle_i / 60)."""
    cycle_min = 2 * dist_to_store / speed_kmh * 60 + handover_min
    load = pd.Series(orders_per_hour * cycle_min / 60).groupby(store_of_cell).sum()
    return int(np.ceil(load).sum()), load


def main():
    cfg = load_config()
    case, solver = cfg["case"], cfg["solver"]
    D, C, dist, detour = load_instance()
    fixed, te = fixed_minutes(case)
    pop = D["pop"].to_numpy()
    mid = lambda k: case[k][len(case[k]) // 2] if isinstance(case[k], list) else case[k]
    daily, peak_share = mid("bengaluru_daily_orders"), mid("peak_hour_share")
    F, c_r, util = mid("dark_store_fixed_cost_inr_month"), mid("rider_cost_inr_hour"), mid("rider_utilisation")
    lam = pop / pop.sum() * daily * peak_share  # orders/hour at peak per demand cell

    rows = []
    for T in case["promise_min"]:
        for v in case["rider_speed_kmh"]:
            r = ride_radius_km(T, v, fixed)
            res = set_covering(coverage_sets(dist, r), pop, solver=solver["name"],
                               time_limit_s=solver["time_limit_s"])
            store, d = nearest_open(dist, res.open_sites)
            riders, _ = riders_needed(d, store, lam, v, te["handover_min"])
            row = {"promise_min": T, "speed_kmh": v, "radius_km": round(r, 3),
                   "stores": len(res.open_sites), "pop_covered_share": round(res.covered_weight_share, 4),
                   "uncoverable_cells": len(res.uncoverable),
                   "mean_ride_km": round(float(np.average(d, weights=pop)), 3),
                   "peak_orders_per_hour": round(float(lam.sum())), "riders_peak": riders,
                   "status": res.status}
            cycle_h = float(np.average(2 * d / v + te["handover_min"] / 60, weights=pop))
            row["store_cost_cr_month"] = round(row["stores"] * F / 1e7, 3)
            row["rider_cost_cr_month"] = round(daily * cycle_h / util * c_r * 30 / 1e7, 3)
            row["total_cost_cr_month"] = round(row["store_cost_cr_month"] + row["rider_cost_cr_month"], 3)
            rows.append(row)
            print(row)

    df = pd.DataFrame(rows)
    out = ROOT / "results/e1_price_of_speed.csv"
    df.to_csv(out, index=False)
    meta = {"fixed_minutes": fixed, "pert_means": te, "detour": detour, "daily_orders": daily,
            "peak_hour_share": peak_share, "store_cost_inr_month": F, "rider_cost_inr_hour": c_r,
            "rider_utilisation": util}
    (ROOT / "results/e1_meta.json").write_text(json.dumps(meta, indent=2))

    fig, axes = plt.subplots(1, 3, figsize=(13, 3.6))
    for v, g in df.groupby("speed_kmh"):
        axes[0].plot(g["promise_min"], g["stores"], marker="o", label=f"{v} km/h")
        axes[1].plot(g["promise_min"], g["riders_peak"], marker="o", label=f"{v} km/h")
        axes[2].plot(g["promise_min"], g["total_cost_cr_month"], marker="o", label=f"{v} km/h")
    axes[0].set_ylabel("Dark stores needed (set covering)")
    axes[1].set_ylabel("Riders at peak hour")
    axes[2].set_ylabel("Monthly cost (INR crore)")
    for ax in axes:
        ax.set_xlabel("Delivery promise (min)")
        ax.set_xticks(case["promise_min"])
        ax.grid(alpha=0.3)
    axes[0].legend(title="Safe rider speed")
    fig.tight_layout()
    fig.savefig(ROOT / "results/e1_price_of_speed.png", dpi=200)
    print(f"\nWrote {out} and results/e1_price_of_speed.png")


if __name__ == "__main__":
    main()
