"""CPM / PERT project scheduling and LP-based crashing.

Activities are given as a dict:
    {"A": {"duration": 3, "pred": []}, "B": {"duration": 4, "pred": ["A"]}, ...}
PERT activities give three-point estimates instead of `duration`:
    {"a": optimistic, "m": most_likely, "b": pessimistic}
Crashing adds per-activity "crash_duration" and "crash_cost_per_unit".
"""

import math
from dataclasses import dataclass
from graphlib import TopologicalSorter

import pulp

from orpaper.solver import check_optimal, get_solver


@dataclass
class CPMResult:
    makespan: float
    es: dict
    ef: dict
    ls: dict
    lf: dict
    slack: dict
    critical_path: list[str]


def _order(acts):
    return list(TopologicalSorter({k: v["pred"] for k, v in acts.items()}).static_order())


def cpm(acts, durations=None) -> CPMResult:
    """Forward/backward pass. `durations` overrides activity durations if given."""
    dur = durations or {k: v["duration"] for k, v in acts.items()}
    order = _order(acts)
    succ = {k: [] for k in acts}
    for k, v in acts.items():
        for p in v["pred"]:
            succ[p].append(k)

    es, ef = {}, {}
    for k in order:
        es[k] = max((ef[p] for p in acts[k]["pred"]), default=0.0)
        ef[k] = es[k] + dur[k]
    makespan = max(ef.values())

    ls, lf = {}, {}
    for k in reversed(order):
        lf[k] = min((ls[s] for s in succ[k]), default=makespan)
        ls[k] = lf[k] - dur[k]

    slack = {k: ls[k] - es[k] for k in acts}
    critical = [k for k in order if abs(slack[k]) < 1e-9]
    return CPMResult(makespan, es, ef, ls, lf, slack, critical)


def pert_estimates(acts):
    """Beta-distribution mean and variance per activity: te=(a+4m+b)/6, var=((b-a)/6)^2."""
    te = {k: (v["a"] + 4 * v["m"] + v["b"]) / 6 for k, v in acts.items()}
    var = {k: ((v["b"] - v["a"]) / 6) ** 2 for k, v in acts.items()}
    return te, var


def pert(acts, deadline=None):
    """Return (CPMResult on expected times, project std dev, P(finish <= deadline))."""
    te, var = pert_estimates(acts)
    res = cpm(acts, durations=te)
    sigma = math.sqrt(sum(var[k] for k in res.critical_path))
    prob = None
    if deadline is not None:
        z = (deadline - res.makespan) / sigma if sigma > 0 else math.inf
        prob = 0.5 * (1 + math.erf(z / math.sqrt(2)))
    return res, sigma, prob


@dataclass
class CrashResult:
    makespan: float
    crash_cost: float
    crashed_by: dict  # activity -> units reduced
    status: str


def crash(acts, deadline, solver="HiGHS", time_limit_s=None) -> CrashResult:
    """Minimum-cost crashing LP to meet `deadline`.

        min  sum_k cc_k y_k
        s.t. t_k >= t_p + d_k - y_k     for each precedence p -> k
             t_k >= d_k - y_k           (start nodes)
             t_k <= deadline
             0 <= y_k <= d_k - crash_d_k
    where t_k is the finish time of activity k and y_k the crash amount.
    """
    prob = pulp.LpProblem("crashing", pulp.LpMinimize)
    t = {k: pulp.LpVariable(f"t_{k}", lowBound=0) for k in acts}
    y = {k: pulp.LpVariable(f"y_{k}", lowBound=0,
                            upBound=v["duration"] - v.get("crash_duration", v["duration"]))
         for k, v in acts.items()}
    prob += pulp.lpSum(v.get("crash_cost_per_unit", 0) * y[k] for k, v in acts.items())
    for k, v in acts.items():
        prob += t[k] >= v["duration"] - y[k], f"start_{k}"
        for p in v["pred"]:
            prob += t[k] >= t[p] + v["duration"] - y[k], f"prec_{p}_{k}"
        prob += t[k] <= deadline, f"deadline_{k}"

    prob.solve(get_solver(solver, time_limit_s))
    check_optimal(prob)
    crashed = {k: round(y[k].value(), 6) for k in acts if y[k].value() > 1e-9}
    return CrashResult(
        makespan=max(t[k].value() for k in acts),
        crash_cost=pulp.value(prob.objective) or 0.0,
        crashed_by=crashed,
        status=pulp.LpStatus[prob.status],
    )
