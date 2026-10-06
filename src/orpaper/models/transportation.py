"""Transportation problem: LP formulation plus textbook starting-solution heuristics.

Formulation
    min  sum_ij c_ij x_ij
    s.t. sum_j x_ij <= s_i   (supply)       for each source i
         sum_i x_ij >= d_j   (demand)       for each destination j
         x_ij >= 0

Unbalanced instances are handled by adding a dummy source/destination with
zero cost (or `shortage_penalty` for unmet demand), which mirrors the textbook
treatment and keeps the LP feasible.
"""

from dataclasses import dataclass

import numpy as np
import pulp

from orpaper.solver import check_optimal, get_solver


@dataclass
class TransportationResult:
    cost: float
    flows: np.ndarray  # shape (m, n), original sources x destinations
    unmet_demand: np.ndarray  # per destination; > 0 only if supply < demand
    unused_supply: np.ndarray  # per source
    status: str


def balance(supply, demand, cost, shortage_penalty=0.0):
    """Add a dummy row/column so total supply equals total demand."""
    supply = np.asarray(supply, float)
    demand = np.asarray(demand, float)
    cost = np.asarray(cost, float)
    gap = supply.sum() - demand.sum()
    if gap > 0:  # excess supply -> dummy destination
        demand = np.append(demand, gap)
        cost = np.hstack([cost, np.zeros((len(supply), 1))])
    elif gap < 0:  # excess demand -> dummy source
        supply = np.append(supply, -gap)
        cost = np.vstack([cost, np.full((1, len(demand)), shortage_penalty)])
    return supply, demand, cost


def solve_transportation(supply, demand, cost, shortage_penalty=0.0,
                         solver="HiGHS", time_limit_s=None) -> TransportationResult:
    m, n = np.shape(cost)
    s, d, c = balance(supply, demand, cost, shortage_penalty)
    M, N = c.shape

    prob = pulp.LpProblem("transportation", pulp.LpMinimize)
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", lowBound=0) for i in range(M) for j in range(N)}
    prob += pulp.lpSum(c[i, j] * x[i, j] for i in range(M) for j in range(N))
    for i in range(M):
        prob += pulp.lpSum(x[i, j] for j in range(N)) == s[i], f"supply_{i}"
    for j in range(N):
        prob += pulp.lpSum(x[i, j] for i in range(M)) == d[j], f"demand_{j}"

    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)

    X = np.array([[x[i, j].value() or 0.0 for j in range(N)] for i in range(M)])
    unmet = X[m, :n] if M > m else np.zeros(n)
    unused = X[:m, n] if N > n else np.zeros(m)
    return TransportationResult(
        cost=float(np.sum(X[:m, :n] * np.asarray(cost))) + shortage_penalty * float(unmet.sum()),
        flows=X[:m, :n],
        unmet_demand=unmet,
        unused_supply=unused,
        status=pulp.LpStatus[prob.status],
    )


def northwest_corner(supply, demand):
    """Initial basic feasible solution (balanced input required)."""
    s, d = np.array(supply, float), np.array(demand, float)
    X = np.zeros((len(s), len(d)))
    i = j = 0
    while i < len(s) and j < len(d):
        q = min(s[i], d[j])
        X[i, j] = q
        s[i] -= q
        d[j] -= q
        if s[i] == 0:
            i += 1
        else:
            j += 1
    return X


def vogel_approximation(supply, demand, cost):
    """Vogel's Approximation Method (balanced input required)."""
    s, d = np.array(supply, float), np.array(demand, float)
    c = np.array(cost, float)
    X = np.zeros_like(c)
    rows, cols = set(range(len(s))), set(range(len(d)))

    def penalty(vals):
        v = sorted(vals)
        return v[1] - v[0] if len(v) > 1 else v[0]

    while rows and cols:
        rp = {i: penalty([c[i, j] for j in cols]) for i in rows}
        cp = {j: penalty([c[i, j] for i in rows]) for j in cols}
        best_r = max(rp, key=rp.get)
        best_c = max(cp, key=cp.get)
        if rp[best_r] >= cp[best_c]:
            i = best_r
            j = min(cols, key=lambda jj: c[i, jj])
        else:
            j = best_c
            i = min(rows, key=lambda ii: c[ii, j])
        q = min(s[i], d[j])
        X[i, j] = q
        s[i] -= q
        d[j] -= q
        if s[i] == 0:
            rows.discard(i)
        if d[j] == 0:
            cols.discard(j)
    return X
