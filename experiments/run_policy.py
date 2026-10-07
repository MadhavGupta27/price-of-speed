"""Policy experiments (paper §6.6-6.7), on the Bengaluru instance at safe speed 15 km/h.

    uv run python experiments/run_policy.py

E7  Fragmentation: maximal covering with P stores (P swept; 165 = Blinkit's Bengaluru
    count, 440 = all three platforms) -> share of residents reachable within T = 10, 15.
E8  'Realistic promise' policy: promise 10 min wherever an address is reachable within
    the 10-minute safe radius of a candidate site, 15 min elsewhere; compared with
    uniform 10- and 15-minute promises (M1-cost design).
"""

import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from run_design import CASE, FIG, RES, SOLVER, Instance, design, mid, pert_inputs
from orpaper.models.covering import coverage_sets, maximal_covering, ride_radius_km
from orpaper.models.design import rider_cost_matrix, solve_design

V = 15


def run_fragmentation(inst):
    fixed = sum(pert_inputs()[0].values())
    rows = []
    for T in (10, 15):
        cov = coverage_sets(inst.dist, ride_radius_km(T, V, fixed))
        for P in (50, 100, 165, 250, 350, 440):
            res = maximal_covering(cov, inst.pop, P, solver=SOLVER["name"], time_limit_s=SOLVER["time_limit_s"])
            rows.append({"promise_min": T, "stores": P, "reachable_share": round(res.covered_weight_share, 4),
                         "status": res.status})
            print("E7", rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "fragmentation_mclp.csv", index=False)

    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    for T, g in df.groupby("promise_min"):
        ax.plot(g["stores"], 100 * g["reachable_share"], marker="o", label=f"$T$ = {T} min")
    for P, lab in ((165, "one platform\n(Blinkit, 165)"), (440, "three platforms\n(440)")):
        ax.axvline(P, color="grey", lw=0.8, ls="--")
        ax.text(P + 5, 40, lab, fontsize=7, color="grey")
    ax.set_xlabel("Dark stores (maximal covering, best locations)")
    ax.set_ylabel("Residents reachable (%)")
    ax.set_ylim(0, 102)
    ax.grid(alpha=0.3)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "fragmentation.pdf")
    plt.close(fig)
    return df


def run_realistic_promise(inst):
    te = pert_inputs()[0]
    fixed = sum(te.values())
    r10, r15 = ride_radius_km(10, V, fixed), ride_radius_km(15, V, fixed)
    reach10 = (inst.dist <= r10).any(axis=1)          # 10 min possible from some candidate site
    radius = np.where(reach10, r10, r15)
    daily = mid("bengaluru_daily_orders")
    q = inst.pop / inst.pop.sum() * daily
    cost = rider_cost_matrix(inst.dist, q, V, te["handover_min"], mid("rider_utilisation"), mid("rider_cost_inr_hour"))
    res = solve_design(inst.dist, radius, cost, mid("dark_store_fixed_cost_inr_month"),
                       solver=SOLVER["name"], time_limit_s=SOLVER["time_limit_s"])
    served = res.assign >= 0
    total = res.store_cost + res.rider_cost
    mixed = {"policy": "10 min where reachable, else 15", "stores": len(res.open_sites),
             "share_promised_10": round(float(inst.pop[reach10].sum() / inst.pop.sum()), 4),
             "served_share": round(float(inst.pop[served].sum() / inst.pop.sum()), 4),
             "cost_per_order_inr": round(total / (q[served].sum() * 30), 2),
             "total_cost_cr": round(total / 1e7, 3), "status": res.status}
    rows = [mixed]
    for T in (10, 15):
        _, r = design(inst, T, V)
        rows.append({"policy": f"uniform {T} min", "stores": r["stores"],
                     "share_promised_10": 1.0 if T == 10 else 0.0, "served_share": r["served_share"],
                     "cost_per_order_inr": r["cost_per_order_inr"], "total_cost_cr": r["total_cost_cr"],
                     "status": r["status"]})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "realistic_promise.csv", index=False)
    print(df.to_string(index=False))
    return df


def main():
    inst = Instance()
    run_fragmentation(inst)
    run_realistic_promise(inst)


if __name__ == "__main__":
    main()
