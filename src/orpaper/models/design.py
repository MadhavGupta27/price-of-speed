"""Coverage-constrained cost-minimising dark-store network design (paper model M1-cost).

    min  F * sum_j y_j + sum_{(i,j) in A} c_ij x_ij  (+ M * sum_i u_i)
    s.t. sum_{j:(i,j) in A} x_ij + u_i = 1     every demand cell is served or reported unserved
         x_ij <= y_j                           (strong linking)
         sum_i q_i x_ij <= K y_j               (optional store capacity)
         x_ij >= 0, y_j in {0,1}, u_i >= 0
where A = {(i, j) : d_ij <= r(T, v)} (the promise is a hard reachability limit),
c_ij is the monthly rider cost of serving cell i from store j, and u_i absorbs
cells no candidate can reach (penalty M) so the model stays feasible.

Without capacity, x is integral at optimum (each cell picks its cheapest open
store), so x is continuous; the model is an uncapacitated facility location
problem restricted to reachable pairs.
"""

from dataclasses import dataclass

import numpy as np
import pulp

from orpaper.solver import check_optimal, get_solver


@dataclass
class DesignResult:
    open_sites: list[int]
    assign: np.ndarray        # store index per demand cell, -1 if unserved
    store_cost: float
    rider_cost: float
    unserved_cells: list[int]
    status: str
    mip_gap: float | None
    n_arcs: int


def rider_cost_matrix(dist_km, daily_orders, speed_kmh, handover_min, utilisation,
                      cost_per_hour, days=30):
    """Monthly rider cost of serving each cell's daily orders from each site.

    Round trip at safe speed plus handover, inflated by 1/utilisation because riders
    are paid per logged-in hour (idle time included)."""
    cycle_h = 2 * np.asarray(dist_km) / speed_kmh + handover_min / 60
    return np.asarray(daily_orders)[:, None] * cycle_h / utilisation * cost_per_hour * days


def solve_design(dist_km, radius_km, assign_cost, fixed_cost, capacity=None,
                 demand=None, unserved_penalty=None, solver="HiGHS", time_limit_s=None,
                 mip_gap=1e-3) -> DesignResult:
    d = np.asarray(dist_km)
    C = np.asarray(assign_cost)
    n, m = d.shape
    arcs = np.argwhere(d <= radius_km)
    M = unserved_penalty if unserved_penalty is not None else 10 * (C.max() + fixed_cost)

    prob = pulp.LpProblem("design", pulp.LpMinimize)
    y = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(m)]
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0) for i, j in arcs}
    u = [pulp.LpVariable(f"u_{i}", lowBound=0) for i in range(n)]

    by_cell = [[] for _ in range(n)]
    by_site = [[] for _ in range(m)]
    for i, j in arcs:
        by_cell[i].append(j)
        by_site[j].append(i)

    prob += (fixed_cost * pulp.lpSum(y)
             + pulp.lpSum(C[i, j] * v for (i, j), v in x.items())
             + M * pulp.lpSum(u))
    for i in range(n):
        prob += pulp.lpSum(x[i, j] for j in by_cell[i]) + u[i] == 1, f"serve_{i}"
    for (i, j), v in x.items():
        prob += v <= y[j], f"link_{i}_{j}"
    if capacity is not None:
        q = np.asarray(demand)
        for j in range(m):
            if by_site[j]:
                prob += pulp.lpSum(q[i] * x[i, j] for i in by_site[j]) <= capacity * y[j], f"cap_{j}"

    s = get_solver(solver, time_limit_s)
    if hasattr(s, "optionsDict"):
        s.optionsDict["mip_rel_gap"] = mip_gap
    prob.solve(s)
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        check_optimal(prob)

    open_sites = [j for j in range(m) if y[j].value() > 0.5]
    assign = np.full(n, -1)
    for i in range(n):
        if by_cell[i]:
            j_best = max(by_cell[i], key=lambda j: x[i, j].value() or 0)
            if (x[i, j_best].value() or 0) > 0.5:
                assign[i] = j_best
    served = assign >= 0
    rider = float(C[np.flatnonzero(served), assign[served]].sum())
    return DesignResult(open_sites, assign, fixed_cost * len(open_sites), rider,
                        np.flatnonzero(~served).tolist(), status, None, len(arcs))
