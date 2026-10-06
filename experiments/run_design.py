"""Main experiments for the paper (docs/paper-plan.md §5), on the Bengaluru instance.

    uv run python experiments/run_design.py            # everything
    uv run python experiments/run_design.py --only e1  # e1 | grid | pert | assign | transport | tornado

E1      M1-cost design over promise T x safe speed v (+ M2 rider sizing)
GRID    robustness: candidate sites on a ~0.9 km lattice of populated cells (T = 10, 15)
PERT    M5: P(order fulfilled within T) and speed needed for 95% on-time
ASSIGN  M4: peak 10-minute batch at a representative store, optimal vs FIFO
TRANS   M3: replenishment from 3 mother hubs, LP vs Vogel / north-west corner
TORNADO one-at-a-time sensitivity of total monthly cost at the base case

Outputs: results/*.csv|json and paper figures in paper/figures/.
"""

import argparse
import json
import math

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from orpaper.config import ROOT, load_config
from orpaper.data.osrm import haversine_matrix
from orpaper.models.assignment import solve_assignment
from orpaper.models.covering import ride_radius_km
from orpaper.models.cpm_pert import pert_estimates
from orpaper.models.design import rider_cost_matrix, solve_design
from orpaper.models.transportation import northwest_corner, solve_transportation, vogel_approximation

PROC, RES, FIG = ROOT / "data/processed", ROOT / "results", ROOT / "paper/figures"
CFG = load_config()
CASE, SOLVER = CFG["case"], CFG["solver"]
RNG_SEED = CFG["seed"]


def mid(k):
    v = CASE[k]
    return v[len(v) // 2] if isinstance(v, list) else v


def pert_inputs(shift_pick_pack=0.0):
    acts = {k: {**CASE[k], "pred": []} for k in ("pick_pack_min", "rider_assign_min", "handover_min")}
    if shift_pick_pack:
        acts["pick_pack_min"] = {k: (v + shift_pick_pack if k in "amb" else v)
                                 for k, v in acts["pick_pack_min"].items()}
    te, var = pert_estimates(acts)
    return te, var


class Instance:
    def __init__(self, detour=None, grid_candidates=False):
        self.D = pd.read_csv(PROC / "blr_demand_cells.csv")
        if grid_candidates:
            # every other demand cell in each direction (~0.9 km lattice): "a store anywhere"
            keep = (self.D["row"] % 2 == 0) & (self.D["col"] % 2 == 0)
            self.C = self.D.loc[keep, ["lat", "lon"]].reset_index(drop=True)
        else:
            self.C = pd.read_csv(PROC / "blr_candidates.csv")
        cal = json.loads((PROC / "detour_calibration.json").read_text())
        self.detour = detour or cal["detour_median"]
        pts = np.vstack([self.D[["lat", "lon"]].to_numpy(), self.C[["lat", "lon"]].to_numpy()])
        n = len(self.D)
        self.dist = haversine_matrix(pts)[:n, n:] * self.detour
        self.pop = self.D["pop"].to_numpy()


def design(inst, T, v, daily=None, F=None, c_r=None, util=None, te=None):
    daily = daily or mid("bengaluru_daily_orders")
    F, c_r, util = F or mid("dark_store_fixed_cost_inr_month"), c_r or mid("rider_cost_inr_hour"), util or mid("rider_utilisation")
    te = te or pert_inputs()[0]
    fixed = sum(te.values())
    r = ride_radius_km(T, v, fixed)
    q = inst.pop / inst.pop.sum() * daily
    cost = rider_cost_matrix(inst.dist, q, v, te["handover_min"], util, c_r)
    res = solve_design(inst.dist, r, cost, F, solver=SOLVER["name"], time_limit_s=SOLVER["time_limit_s"] * 5)
    served = res.assign >= 0
    d_served = inst.dist[np.flatnonzero(served), res.assign[served]]
    peak = q * mid("peak_hour_share")
    cycle_min = 2 * d_served / v * 60 + te["handover_min"]
    load = pd.Series(peak[served] * cycle_min / 60).groupby(res.assign[served]).sum()
    served_orders = q[served].sum()
    return res, {
        "promise_min": T, "speed_kmh": v, "radius_km": round(r, 3),
        "stores": len(res.open_sites),
        "served_share": round(float(inst.pop[served].sum() / inst.pop.sum()), 4),
        "mean_ride_km": round(float(np.average(d_served, weights=q[served])), 3),
        "riders_peak": int(np.ceil(load).sum()),
        "orders_per_store_day": round(float(served_orders / max(1, len(res.open_sites)))),
        "store_cost_cr": round(res.store_cost / 1e7, 3),
        "rider_cost_cr": round(res.rider_cost / 1e7, 3),
        "total_cost_cr": round((res.store_cost + res.rider_cost) / 1e7, 3),
        "cost_per_order_inr": round((res.store_cost + res.rider_cost) / (served_orders * 30), 2),
        "status": res.status, "arcs": res.n_arcs,
    }


# ---------------------------------------------------------------- E1
def run_e1(inst):
    rows, designs = [], {}
    for T in CASE["promise_min"]:
        for v in CASE["rider_speed_kmh"]:
            res, row = design(inst, T, v)
            rows.append(row)
            designs[(T, v)] = res
            print("E1", row, flush=True)
            pd.DataFrame({"site": res.open_sites,
                          "lat": inst.C.iloc[res.open_sites]["lat"].to_numpy(),
                          "lon": inst.C.iloc[res.open_sites]["lon"].to_numpy()}
                         ).to_csv(RES / f"design_T{T}_v{v}_sites.csv", index=False)
            pd.DataFrame({"cell": inst.D["cell_id"], "assign": res.assign}
                         ).to_csv(RES / f"design_T{T}_v{v}_assign.csv", index=False)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "e1_design.csv", index=False)

    # price per minute of speed (consecutive promises, same speed; cost per served order)
    ppm = []
    for v, g in df.sort_values("promise_min").groupby("speed_kmh"):
        g = g.reset_index(drop=True)
        for a, b in zip(g.index[:-1], g.index[1:]):
            ppm.append({"speed_kmh": v, "from_min": int(g.loc[b, "promise_min"]),
                        "to_min": int(g.loc[a, "promise_min"]),
                        "extra_cost_per_order_inr": round(g.loc[a, "cost_per_order_inr"] - g.loc[b, "cost_per_order_inr"], 2),
                        "inr_per_order_per_minute": round((g.loc[a, "cost_per_order_inr"] - g.loc[b, "cost_per_order_inr"])
                                                          / (g.loc[b, "promise_min"] - g.loc[a, "promise_min"]), 2)})
    pd.DataFrame(ppm).to_csv(RES / "e1_price_per_minute.csv", index=False)

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for v, g in df.groupby("speed_kmh"):
        axes[0].plot(g["promise_min"], g["cost_per_order_inr"], marker="o", label=f"{v} km/h")
        axes[1].plot(g["promise_min"], g["stores"], marker="o", label=f"{v} km/h")
        axes[2].plot(g["promise_min"], 100 * g["served_share"], marker="o", label=f"{v} km/h")
    axes[0].set_ylabel("Cost per served order (INR)")
    axes[1].set_ylabel("Dark stores opened")
    axes[2].set_ylabel("Population reachable (%)")
    for ax in axes:
        ax.set_xlabel("Delivery promise $T$ (min)")
        ax.set_xticks(CASE["promise_min"])
        ax.grid(alpha=0.3)
    axes[0].legend(title="Safe speed", fontsize=8)
    fig.tight_layout()
    fig.savefig(FIG / "price_of_speed.pdf")
    plt.close(fig)
    return df, designs


def plot_maps(inst, designs, pairs=((10, 15), (20, 15))):
    fig, axes = plt.subplots(1, len(pairs), figsize=(5 * len(pairs), 4.6))
    for ax, (T, v) in zip(axes, pairs):
        res = designs[(T, v)]
        served = res.assign >= 0
        ax.scatter(inst.D["lon"], inst.D["lat"], c=np.where(served, inst.pop, np.nan), s=3,
                   cmap="Greys", marker="s", linewidths=0)
        ax.scatter(inst.D["lon"][~served], inst.D["lat"][~served], s=3, c="#d95f02", marker="s",
                   linewidths=0, label="not reachable")
        ax.scatter(inst.C.iloc[res.open_sites]["lon"], inst.C.iloc[res.open_sites]["lat"], s=6,
                   c="#1b9e77", label="dark store")
        ax.set_title(f"$T$ = {T} min, $v$ = {v} km/h: {len(res.open_sites)} stores", fontsize=10)
        ax.set_aspect(1 / math.cos(math.radians(12.97)))
        ax.set_xticks([])
        ax.set_yticks([])
    axes[0].legend(loc="lower left", fontsize=8, markerscale=3)
    fig.tight_layout()
    fig.savefig(FIG / "network_maps.pdf")
    plt.close(fig)


class SavedDesign:
    def __init__(self, inst, T, v):
        sites = pd.read_csv(RES / f"design_T{T}_v{v}_sites.csv")
        self.open_sites = sites["site"].tolist()
        self.assign = pd.read_csv(RES / f"design_T{T}_v{v}_assign.csv")["assign"].to_numpy()


def load_designs(inst):
    return {(T, v): SavedDesign(inst, T, v) for T in CASE["promise_min"] for v in CASE["rider_speed_kmh"]}


# ---------------------------------------------------------------- GRID
def run_grid():
    inst = Instance(grid_candidates=True)
    rows = []
    for T in (10, 15):
        _, row = design(inst, T, 15)
        row["candidates"] = f"grid ({len(inst.C)} sites)"
        rows.append(row)
        print("GRID", row, flush=True)
    pd.DataFrame(rows).to_csv(RES / "grid_robustness.csv", index=False)


# ---------------------------------------------------------------- PERT
def pert_on_time(ride_min, te, var, T):
    a, m, b = np.percentile(ride_min, [5, 50, 95])
    mu = sum(te.values()) + (a + 4 * m + b) / 6
    sd = math.sqrt(sum(var.values()) + ((b - a) / 6) ** 2)
    return mu, sd, 0.5 * (1 + math.erf((T - mu) / (sd * math.sqrt(2))))


def run_pert(inst, designs):
    te, var = pert_inputs()
    q = inst.pop
    rows = []
    for (T, v), res in designs.items():
        served = res.assign >= 0
        d = inst.dist[np.flatnonzero(served), res.assign[served]]
        # demand-weighted ride-time sample
        rng = np.random.default_rng(RNG_SEED)
        sample = rng.choice(d, size=20000, p=q[served] / q[served].sum()) / v * 60
        mu, sd, p = pert_on_time(sample, te, var, T)
        lo, hi = 5.0, 60.0  # speed needed for 95% on time with this network's distances
        for _ in range(50):
            s = (lo + hi) / 2
            if pert_on_time(sample * v / s, te, var, T)[2] >= 0.95:
                hi = s
            else:
                lo = s
        rows.append({"promise_min": T, "speed_kmh": v, "mean_min": round(mu, 2), "sd_min": round(sd, 2),
                     "p_on_time": round(p, 4), "speed_for_95pct_kmh": round(hi, 1)})
    df = pd.DataFrame(rows)
    df.to_csv(RES / "pert_reliability.csv", index=False)
    print(df.to_string(index=False))
    return df


# ---------------------------------------------------------------- ASSIGN
def run_assign(inst, designs, v=15, base_T=15, batch_min=10):
    """Peak batch at two stores of the base design (median load; 90th-percentile mean ride
    distance = stressed) x staffing level x promise T."""
    rows = []
    for which in ("median_load", "p90_ride_distance"):
        rows += _assign_at(inst, designs, which, v, base_T, batch_min)
    df = pd.DataFrame(rows)
    df.to_csv(RES / "assignment_peak.csv", index=False)
    print(df.to_string(index=False))
    return df


def _assign_at(inst, designs, which, v, base_T, batch_min):
    te, _ = pert_inputs()
    res = designs[(base_T, v)]
    q = inst.pop / inst.pop.sum() * mid("bengaluru_daily_orders") * mid("peak_hour_share")
    served = res.assign >= 0
    loads = pd.Series(q[served]).groupby(res.assign[served]).sum()
    if which == "median_load":
        store = int(loads.sort_values().index[len(loads) // 2])
    else:
        idx = np.flatnonzero(served)
        mean_d = pd.Series(inst.dist[idx, res.assign[idx]] * q[idx]).groupby(res.assign[idx]).sum() / loads
        store = int(mean_d.sort_values().index[int(0.9 * (len(mean_d) - 1))])
    cells = np.flatnonzero(res.assign == store)
    w = q[cells] / q[cells].sum()
    d_cells = inst.dist[cells, store]
    cycle_mean = float(np.average(2 * d_cells / v * 60 + te["handover_min"], weights=w))
    n = max(2, round(loads[store] * batch_min / 60))
    riders = max(1, math.ceil(loads[store] * cycle_mean / 60))
    rng = np.random.default_rng(RNG_SEED)
    arrive = np.sort(rng.uniform(0, batch_min, n))
    ride = d_cells[rng.choice(len(cells), size=n, p=w)] / v * 60
    ready = arrive + te["pick_pack_min"] + te["rider_assign_min"]
    rng_free = rng.uniform(0, cycle_mean, riders)

    rows = []
    for staffing in (0.4, 0.6, 0.8, 1.0):
        R = max(1, round(riders * staffing))
        free0 = rng_free[:R]
        k = math.ceil(n / R) + 1                        # successive trips per rider in the window
        slot_free = np.concatenate([free0 + s_ * cycle_mean for s_ in range(k)])
        for T in (10, 15, 20):
            def lateness(slot, o):
                depart = max(slot_free[slot], ready[o])
                return max(0.0, depart + ride[o] + te["handover_min"] - (arrive[o] + T))
            cost = np.array([[lateness(s_, o) + 1e-3 * slot_free[s_] for o in range(n)]
                             for s_ in range(len(slot_free))])
            opt = solve_assignment(cost, solver=SOLVER["name"])
            late_opt = np.array([lateness(s_, o) for s_, o in opt.pairs])
            free, late_fifo = list(slot_free), []
            for o in np.argsort(ready):                 # FIFO: earliest-ready order takes earliest-free slot
                s_ = int(np.argmin(free))
                late_fifo.append(lateness(s_, o))
                free[s_] = np.inf
            late_fifo = np.array(late_fifo)
            # speed a rider would need so that the optimal plan's late orders arrive on time
            need = [ (ride[o] * v / 60) / max(1e-9, (ride[o] - lateness(s_, o)) / 60)
                     for s_, o in opt.pairs if lateness(s_, o) > 1e-9 and ride[o] - lateness(s_, o) > 0 ]
            rows.append({"store_type": which, "mean_ride_km": round(float(np.average(d_cells, weights=w)), 2),
                         "staffing": staffing, "riders": R, "promise_min": T, "store": store,
                         "orders_in_batch": n,
                         "on_time_opt": round(float((late_opt <= 1e-9).mean()), 3),
                         "on_time_fifo": round(float((late_fifo <= 1e-9).mean()), 3),
                         "mean_late_min_opt": round(float(late_opt.mean()), 2),
                         "mean_late_min_fifo": round(float(late_fifo.mean()), 2),
                         "speed_to_recover_late_kmh_median": round(float(np.median(need)), 1) if need else None})
    return rows


# ---------------------------------------------------------------- TRANSPORT
def run_transport(inst, designs, T=15, v=15, n_hubs=3):
    res = designs[(T, v)]
    sites = inst.C.iloc[res.open_sites].reset_index(drop=True)
    q = inst.pop / inst.pop.sum() * mid("bengaluru_daily_orders")
    served = res.assign >= 0
    store_orders = pd.Series(q[served]).groupby(res.assign[served]).sum().reindex(res.open_sites).fillna(0).to_numpy()
    # hubs: weighted k-means of store locations, snapped to the nearest OSM warehouse
    cand = pd.read_csv(PROC / "blr_candidates.csv")
    wh = cand[cand["kinds"].str.contains("warehouse")].reset_index(drop=True)
    X = sites[["lat", "lon"]].to_numpy()
    rng = np.random.default_rng(RNG_SEED)
    cent = X[rng.choice(len(X), n_hubs, replace=False)]
    for _ in range(100):
        lab = np.argmin(((X[:, None] - cent[None]) ** 2).sum(-1), axis=1)
        cent = np.array([np.average(X[lab == h], axis=0, weights=store_orders[lab == h] + 1e-9) for h in range(n_hubs)])
    hub_idx = [int(np.argmin(((wh[["lat", "lon"]].to_numpy() - c) ** 2).sum(1))) for c in cent]
    hubs = wh.iloc[hub_idx].reset_index(drop=True)
    dist = haversine_matrix(np.vstack([hubs[["lat", "lon"]].to_numpy(), X]))[:n_hubs, n_hubs:] * inst.detour
    # balanced supplies: total demand split evenly (equal-capacity hubs)
    demand = np.round(store_orders).astype(int)
    supply = np.full(n_hubs, demand.sum() // n_hubs)
    supply[: demand.sum() - supply.sum()] += 1
    lp = solve_transportation(supply, demand, dist, solver=SOLVER["name"])
    vam = vogel_approximation(supply, demand, dist)
    nw = northwest_corner(supply, demand)
    out = {"T": T, "v": v, "hubs": hubs[["site_id", "lat", "lon", "kinds"]].to_dict("records"),
           "stores": len(sites), "daily_orders": int(demand.sum()),
           "lp_order_km": round(lp.cost), "vogel_order_km": round(float((vam * dist).sum())),
           "nw_order_km": round(float((nw * dist).sum())),
           "nearest_hub_order_km": round(float((demand * dist.min(0)).sum())),
           "lp_mean_km_per_order": round(lp.cost / demand.sum(), 3)}
    (RES / "transport_replenishment.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    return out


# ---------------------------------------------------------------- TORNADO
def run_tornado(T=15, v=15):
    inst = Instance()
    _, base = design(inst, T, v)
    cal = json.loads((PROC / "detour_calibration.json").read_text())
    rng_ = lambda k: (CASE[k][0], CASE[k][-1])
    cases = {
        "Daily orders (450k-750k)": [dict(daily=x) for x in rng_("bengaluru_daily_orders")],
        "Store cost (INR 6-11 L/month)": [dict(F=x) for x in rng_("dark_store_fixed_cost_inr_month")],
        "Rider cost (INR 102-154/h)": [dict(c_r=x) for x in rng_("rider_cost_inr_hour")],
        "Rider utilisation (0.5-0.7)": [dict(util=x) for x in rng_("rider_utilisation")],
        "Pick/pack time (-1/+1 min)": [dict(te=pert_inputs(s)[0]) for s in (-1.0, 1.0)],
    }
    rows = []
    for name, (lo, hi) in cases.items():
        r_lo, r_hi = design(inst, T, v, **lo)[1], design(inst, T, v, **hi)[1]
        rows.append({"param": name, "low": r_lo["cost_per_order_inr"], "high": r_hi["cost_per_order_inr"],
                     "stores_low": r_lo["stores"], "stores_high": r_hi["stores"]})
        print("TORNADO", rows[-1], flush=True)
    for name, det in (("Road detour (IQR 1.41-1.81)", (cal["detour_p25"], cal["detour_p75"])),):
        r_lo = design(Instance(detour=det[0]), T, v)[1]
        r_hi = design(Instance(detour=det[1]), T, v)[1]
        rows.append({"param": name, "low": r_lo["cost_per_order_inr"], "high": r_hi["cost_per_order_inr"],
                     "stores_low": r_lo["stores"], "stores_high": r_hi["stores"]})
        print("TORNADO", rows[-1], flush=True)
    df = pd.DataFrame(rows)
    df["base"] = base["cost_per_order_inr"]
    df["span"] = (df["high"] - df["low"]).abs()
    df = df.sort_values("span")
    df.to_csv(RES / "tornado.csv", index=False)

    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    b = base["cost_per_order_inr"]
    for k, r in enumerate(df.itertuples()):
        ax.barh(k, r.low - b, left=b, color="#7570b3")
        ax.barh(k, r.high - b, left=b, color="#d95f02")
    ax.axvline(b, color="black", lw=0.8)
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(df["param"], fontsize=8)
    ax.set_xlabel(f"Cost per served order (INR); base = {b:.1f} at T = {T} min, v = {v} km/h")
    fig.tight_layout()
    fig.savefig(FIG / "tornado.pdf")
    plt.close(fig)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["e1", "grid", "pert", "assign", "transport", "tornado"])
    ap.add_argument("--reuse", action="store_true", help="load saved E1 designs instead of re-solving")
    a = ap.parse_args()
    RES.mkdir(exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    want = lambda k: a.only in (None, k)

    inst = Instance()
    designs = None
    if a.reuse:
        designs = load_designs(inst)
    elif any(want(k) for k in ("e1", "pert", "assign", "transport")):
        df, designs = run_e1(inst)
        plot_maps(inst, designs)
    if want("pert"):
        run_pert(inst, designs)
    if want("assign"):
        run_assign(inst, designs)
    if want("transport"):
        run_transport(inst, designs)
    if want("grid"):
        run_grid()
    if want("tornado"):
        run_tornado()


if __name__ == "__main__":
    main()
