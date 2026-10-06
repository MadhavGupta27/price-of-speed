"""Covering location models for dark-store siting (paper model M1).

Coverage: demand cell i is covered by site j if road distance d_ij <= r, where
    r(T, v) = v * (T - fixed_min) / 60      (km)
is the ride radius left after pick/pack, assignment and handover for promise T
(minutes) at safe rider speed v (km/h).

Set covering (SCLP):   min sum_j y_j   s.t. sum_{j in N_i} y_j >= 1   for required i
Maximal covering (MCLP): max sum_i w_i z_i  s.t. z_i <= sum_{j in N_i} y_j,  sum_j y_j = P
"""

from dataclasses import dataclass

import numpy as np
import pulp

from orpaper.solver import check_optimal, get_solver


def ride_radius_km(promise_min: float, speed_kmh: float, fixed_min: float) -> float:
    return max(0.0, speed_kmh * (promise_min - fixed_min) / 60.0)


def coverage_sets(dist, radius_km):
    """Boolean matrix cover[i, j] = dist[i, j] <= radius."""
    return np.asarray(dist) <= radius_km


@dataclass
class CoveringResult:
    open_sites: list[int]
    covered: np.ndarray  # bool per demand cell
    covered_weight_share: float
    uncoverable: list[int]  # demand cells no site can reach (SCLP only)
    status: str


def set_covering(cover, weights=None, solver="HiGHS", time_limit_s=None) -> CoveringResult:
    """Fewest sites covering every coverable demand cell.

    Cells that no candidate can reach within the radius are reported in
    `uncoverable` rather than making the model infeasible.
    """
    cover = np.asarray(cover, bool)
    n, m = cover.shape
    w = np.ones(n) if weights is None else np.asarray(weights, float)
    reachable = cover.any(axis=1)

    prob = pulp.LpProblem("set_covering", pulp.LpMinimize)
    y = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(m)]
    prob += pulp.lpSum(y)
    for i in np.flatnonzero(reachable):
        prob += pulp.lpSum(y[j] for j in np.flatnonzero(cover[i])) >= 1, f"cover_{i}"
    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)

    open_sites = [j for j in range(m) if y[j].value() > 0.5]
    covered = cover[:, open_sites].any(axis=1) if open_sites else np.zeros(n, bool)
    return CoveringResult(open_sites, covered, float(w[covered].sum() / w.sum()),
                          np.flatnonzero(~reachable).tolist(), pulp.LpStatus[prob.status])


def maximal_covering(cover, weights, p: int, solver="HiGHS", time_limit_s=None) -> CoveringResult:
    """Open exactly p sites to maximise covered demand weight."""
    cover = np.asarray(cover, bool)
    w = np.asarray(weights, float)
    n, m = cover.shape
    if p > m:
        raise ValueError(f"p={p} exceeds number of candidate sites {m}")

    prob = pulp.LpProblem("maximal_covering", pulp.LpMaximize)
    y = [pulp.LpVariable(f"y_{j}", cat="Binary") for j in range(m)]
    # z can be continuous in [0, 1]: at optimum it takes 0/1 values given binary y.
    z = [pulp.LpVariable(f"z_{i}", lowBound=0, upBound=1) for i in range(n)]
    prob += pulp.lpSum(w[i] * z[i] for i in range(n))
    for i in range(n):
        prob += z[i] <= pulp.lpSum(y[j] for j in np.flatnonzero(cover[i])), f"cov_{i}"
    prob += pulp.lpSum(y) == p, "p_sites"
    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)

    open_sites = [j for j in range(m) if y[j].value() > 0.5]
    covered = cover[:, open_sites].any(axis=1)
    return CoveringResult(open_sites, covered, float(w[covered].sum() / w.sum()),
                          np.flatnonzero(~cover.any(axis=1)).tolist(), pulp.LpStatus[prob.status])


def nearest_open(dist, open_sites):
    """Index (into open_sites) and distance of each demand cell's nearest open site."""
    d = np.asarray(dist)[:, open_sites]
    k = d.argmin(axis=1)
    return np.asarray(open_sites)[k], d[np.arange(len(d)), k]
