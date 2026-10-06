"""Capacitated Vehicle Routing Problem (CVRP), MILP with MTZ load constraints.

Node 0 is the depot; nodes 1..n are customers.

    min  sum_ij c_ij x_ij
    s.t. sum_j x_ij = 1                         each customer left once
         sum_i x_ij = 1                         each customer entered once
         sum_j x_0j <= K                        fleet size
         sum_j x_0j = sum_i x_i0                vehicles return
         u_j >= u_i + q_j - Q (1 - x_ij)        load propagation / subtour elimination
         q_i <= u_i <= Q
         x_ij binary

Exact MTZ is practical up to ~20-30 customers. For larger instances use the
nearest-neighbour heuristic here as a baseline, or switch to OR-Tools routing.
Time windows for perishable/delivery topics extend the same pattern with
arrival-time variables and big-M constraints.
"""

from dataclasses import dataclass

import numpy as np
import pulp

from orpaper.solver import check_optimal, get_solver


@dataclass
class VRPResult:
    cost: float
    routes: list[list[int]]  # each route starts and ends at depot 0
    vehicles_used: int
    status: str


def route_cost(routes, dist):
    return float(sum(dist[r[k], r[k + 1]] for r in routes for k in range(len(r) - 1)))


def _extract_routes(arcs, n_nodes):
    nxt = {}
    starts = []
    for i, j in arcs:
        if i == 0:
            starts.append(j)
        else:
            nxt[i] = j
    routes = []
    for s in starts:
        r = [0, s]
        while r[-1] != 0:
            r.append(nxt[r[-1]])
        routes.append(r)
    return routes


def solve_cvrp(dist, demand, capacity, n_vehicles, solver="HiGHS",
               time_limit_s=None) -> VRPResult:
    c = np.asarray(dist, float)
    q = np.asarray(demand, float)  # q[0] = 0 for depot
    N = len(q)
    if q[1:].max() > capacity:
        raise ValueError("A single customer's demand exceeds vehicle capacity")

    prob = pulp.LpProblem("cvrp", pulp.LpMinimize)
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary")
         for i in range(N) for j in range(N) if i != j}
    u = {i: pulp.LpVariable(f"u_{i}", lowBound=q[i], upBound=capacity) for i in range(1, N)}

    prob += pulp.lpSum(c[i, j] * v for (i, j), v in x.items())
    for i in range(1, N):
        prob += pulp.lpSum(x[i, j] for j in range(N) if j != i) == 1, f"out_{i}"
        prob += pulp.lpSum(x[j, i] for j in range(N) if j != i) == 1, f"in_{i}"
    prob += pulp.lpSum(x[0, j] for j in range(1, N)) <= n_vehicles, "fleet"
    prob += (pulp.lpSum(x[0, j] for j in range(1, N))
             == pulp.lpSum(x[i, 0] for i in range(1, N))), "return"
    for i in range(1, N):
        for j in range(1, N):
            if i != j:
                prob += u[j] >= u[i] + q[j] - capacity * (1 - x[i, j]), f"mtz_{i}_{j}"

    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)
    arcs = [k for k, v in x.items() if v.value() > 0.5]
    routes = _extract_routes(arcs, N)
    return VRPResult(route_cost(routes, c), routes, len(routes), pulp.LpStatus[prob.status])


def nearest_neighbour(dist, demand, capacity) -> VRPResult:
    """Greedy baseline: extend each route to the nearest feasible customer."""
    c = np.asarray(dist, float)
    q = np.asarray(demand, float)
    unvisited = set(range(1, len(q)))
    routes = []
    while unvisited:
        route, load, cur = [0], 0.0, 0
        while True:
            cands = [j for j in unvisited if load + q[j] <= capacity]
            if not cands:
                break
            cur = min(cands, key=lambda j: c[cur, j])
            route.append(cur)
            load += q[cur]
            unvisited.discard(cur)
        route.append(0)
        routes.append(route)
    return VRPResult(route_cost(routes, c), routes, len(routes), "Heuristic")
