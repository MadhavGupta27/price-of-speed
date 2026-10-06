"""Assignment problem as a 0-1 integer program.

Formulation
    min  sum_ij c_ij x_ij
    s.t. sum_j x_ij <= cap_i   (each agent takes at most cap_i tasks; default 1)
         sum_i x_ij  = 1       (each task assigned exactly once)
         x_ij in {0,1};  x_ij = 0 for forbidden (i, j)

Covers square/rectangular assignment, crew/staff assignment with multi-task
capacity, and infeasible pairings (qualifications, time-window clashes).
"""

from dataclasses import dataclass

import numpy as np
import pulp

from orpaper.solver import check_optimal, get_solver


@dataclass
class AssignmentResult:
    cost: float
    pairs: list[tuple[int, int]]  # (agent, task)
    status: str


def solve_assignment(cost, capacity=None, forbidden=(), maximize=False,
                     solver="HiGHS", time_limit_s=None) -> AssignmentResult:
    c = np.asarray(cost, float)
    m, n = c.shape
    cap = np.ones(m, int) if capacity is None else np.asarray(capacity, int)
    if cap.sum() < n:
        raise ValueError(f"Total agent capacity {cap.sum()} < number of tasks {n}")
    banned = set(forbidden)

    sense = pulp.LpMaximize if maximize else pulp.LpMinimize
    prob = pulp.LpProblem("assignment", sense)
    x = {(i, j): pulp.LpVariable(f"x_{i}_{j}", cat="Binary")
         for i in range(m) for j in range(n) if (i, j) not in banned}
    prob += pulp.lpSum(c[i, j] * v for (i, j), v in x.items())
    for i in range(m):
        prob += pulp.lpSum(v for (a, _), v in x.items() if a == i) <= cap[i], f"agent_{i}"
    for j in range(n):
        prob += pulp.lpSum(v for (_, t), v in x.items() if t == j) == 1, f"task_{j}"

    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)
    pairs = sorted(k for k, v in x.items() if v.value() > 0.5)
    return AssignmentResult(
        cost=float(sum(c[i, j] for i, j in pairs)),
        pairs=pairs,
        status=pulp.LpStatus[prob.status],
    )
