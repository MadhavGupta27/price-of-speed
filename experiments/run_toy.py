"""Phase 6: solve a toy instance for the configured model family and compare
against the textbook/heuristic baseline. Verify the toy result by hand before
scaling up.

    uv run python experiments/run_toy.py [--family vrp] [--size 8]

Swap the synthetic generator for a loader from data/processed/ once real data
exists (PLAN.md Phase 5).
"""

import argparse
import json
import time

import numpy as np

from orpaper.config import ROOT, load_config
from orpaper.data import synthetic
from orpaper.models import assignment, cpm_pert, transportation, vrp


def run(family, size, seed, solver, tl):
    if family == "transportation":
        s, d, c = synthetic.transportation_instance(m=size, n=size + 1, seed=seed)
        opt = transportation.solve_transportation(s, d, c, solver=solver, time_limit_s=tl)
        nw = transportation.northwest_corner(s, d)
        vam = transportation.vogel_approximation(s, d, c)
        return {"instance": {"supply": s, "demand": d, "cost": c},
                "optimal_cost": opt.cost, "flows": opt.flows,
                "baselines": {"northwest_corner": float((nw * c).sum()),
                              "vogel": float((vam * c).sum())}}
    if family == "assignment":
        c = synthetic.assignment_instance(size, size, seed=seed)
        opt = assignment.solve_assignment(c, solver=solver, time_limit_s=tl)
        greedy = float(np.trace(c))  # naive "agent i does task i" baseline
        return {"instance": {"cost": c}, "optimal_cost": opt.cost, "pairs": opt.pairs,
                "baselines": {"identity": greedy}}
    if family == "cpm_pert":
        acts = synthetic.project_network(size, seed=seed)
        det = cpm_pert.cpm(acts)
        res, sigma, p = cpm_pert.pert(acts, deadline=det.makespan)
        cr = cpm_pert.crash(acts, deadline=det.makespan * 0.85, solver=solver, time_limit_s=tl)
        return {"instance": acts, "cpm_makespan": det.makespan, "critical_path": det.critical_path,
                "slack": det.slack, "pert_expected": res.makespan, "pert_sigma": sigma,
                "p_finish_by_cpm_makespan": p,
                "crash_to_85pct": {"cost": cr.crash_cost, "makespan": cr.makespan,
                                   "crashed_by": cr.crashed_by}}
    if family == "vrp":
        coords, q, dist = synthetic.vrp_instance(size, seed=seed)
        cap = int(np.ceil(q.sum() / 3))
        opt = vrp.solve_cvrp(dist, q, cap, n_vehicles=4, solver=solver, time_limit_s=tl)
        nn = vrp.nearest_neighbour(dist, q, cap)
        return {"instance": {"coords": coords, "demand": q, "capacity": cap},
                "optimal_cost": opt.cost, "routes": opt.routes,
                "baselines": {"nearest_neighbour": nn.cost, "nn_routes": nn.routes}}
    raise ValueError(family)


def to_jsonable(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.integer, np.floating)):
        return o.item()
    raise TypeError(type(o))


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=cfg["project"]["model_family"])
    ap.add_argument("--size", type=int, default=6)
    a = ap.parse_args()

    t0 = time.perf_counter()
    out = run(a.family, a.size, cfg["seed"], cfg["solver"]["name"], cfg["solver"]["time_limit_s"])
    out["solve_s"] = time.perf_counter() - t0
    out["solver"] = cfg["solver"]["name"]
    path = ROOT / f"results/toy_{a.family}.json"
    path.write_text(json.dumps(out, indent=2, default=to_jsonable))
    summary = {k: v for k, v in out.items() if k not in ("instance", "flows", "slack")}
    print(json.dumps(summary, indent=2, default=to_jsonable))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
