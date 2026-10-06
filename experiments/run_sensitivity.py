"""Phase 7: one-way sensitivity analysis on 2-3 key parameters.

    uv run python experiments/run_sensitivity.py [--family vrp]

TODO(human): replace the synthetic base instance with the real case-study data
and set the parameter grids to ranges that are meaningful for the case.
"""

import argparse

import numpy as np

from orpaper.config import ROOT, load_config
from orpaper.data import synthetic
from orpaper.models import cpm_pert, transportation, vrp
from orpaper.sensitivity import one_way, plot_one_way


def setup(family, seed, solver):
    if family == "transportation":
        s, d, c = synthetic.transportation_instance(4, 5, seed=seed)

        def evaluate(p):
            r = transportation.solve_transportation(
                s * p["supply_scale"], d * p["demand_scale"], c * p["cost_scale"],
                shortage_penalty=p["shortage_penalty"], solver=solver)
            return {"cost": r.cost, "unmet": float(r.unmet_demand.sum())}

        # Base scenario: demand 10% above supply, so the shortage penalty matters.
        base = {"supply_scale": 1.0, "demand_scale": 1.1, "cost_scale": 1.0, "shortage_penalty": 100}
        grid = {"demand_scale": [0.9, 1.0, 1.1, 1.2, 1.3],
                "supply_scale": [0.8, 0.9, 1.0, 1.1, 1.2],
                "shortage_penalty": [25, 50, 100, 200]}
        return evaluate, base, grid, "cost"

    if family == "vrp":
        coords, q, dist = synthetic.vrp_instance(10, seed=seed)
        cap0 = int(np.ceil(q.sum() / 3))

        def evaluate(p):
            r = vrp.solve_cvrp(dist, q * p["demand_scale"], p["capacity"], p["fleet"],
                               solver=solver, time_limit_s=60)
            return {"cost": r.cost, "vehicles": r.vehicles_used}

        base = {"capacity": cap0, "fleet": 4, "demand_scale": 1.0}
        grid = {"capacity": [int(cap0 * f) for f in (0.8, 0.9, 1.0, 1.2, 1.5)],
                "fleet": [3, 4, 5, 6],
                "demand_scale": [0.8, 0.9, 1.0, 1.1]}
        return evaluate, base, grid, "cost"

    if family == "cpm_pert":
        acts = synthetic.project_network(10, seed=seed)
        T = cpm_pert.cpm(acts).makespan

        def evaluate(p):
            r = cpm_pert.crash(acts, deadline=T * p["deadline_frac"], solver=solver)
            return {"cost": r.crash_cost, "makespan": r.makespan}

        base = {"deadline_frac": 0.9}
        grid = {"deadline_frac": [0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]}
        return evaluate, base, grid, "cost"

    if family == "assignment":
        from orpaper.models import assignment
        c = synthetic.assignment_instance(6, 8, seed=seed)

        def evaluate(p):
            r = assignment.solve_assignment(c, capacity=[p["max_tasks_per_agent"]] * 6, solver=solver)
            return {"cost": r.cost}

        base = {"max_tasks_per_agent": 2}
        grid = {"max_tasks_per_agent": [2, 3, 4]}
        return evaluate, base, grid, "cost"
    raise ValueError(family)


def main():
    cfg = load_config()
    ap = argparse.ArgumentParser()
    ap.add_argument("--family", default=cfg["project"]["model_family"])
    a = ap.parse_args()

    evaluate, base, grid, metric = setup(a.family, cfg["seed"], cfg["solver"]["name"])
    df = one_way(evaluate, base, grid)
    csv = ROOT / f"results/sensitivity_{a.family}.csv"
    png = ROOT / f"results/sensitivity_{a.family}.png"
    df.to_csv(csv, index=False)
    plot_one_way(df[df["status"] == "ok"], metric, png)
    print(df.to_string(index=False))
    print(f"\nWrote {csv} and {png}")


if __name__ == "__main__":
    main()
