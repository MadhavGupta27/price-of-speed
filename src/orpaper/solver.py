import pulp


def get_solver(name: str = "HiGHS", time_limit_s: float | None = None, msg: bool = False):
    """Return a PuLP solver. HiGHS ships via `highspy`; CBC ships with PuLP 2.x."""
    if name == "HiGHS":
        return pulp.HiGHS(msg=msg, timeLimit=time_limit_s)
    if name == "PULP_CBC_CMD":
        return pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit_s)
    raise ValueError(f"Unknown solver {name!r}")


def solution_status(prob: pulp.LpProblem) -> str:
    """'Optimal' only if proven optimal.

    PuLP maps a HiGHS time/iteration limit to LpStatus 'Optimal' with
    sol_status = LpSolutionIntegerFeasible, so LpStatus alone overstates
    optimality; sol_status distinguishes the two.
    """
    if pulp.LpStatus[prob.status] != "Optimal":
        return pulp.LpStatus[prob.status]
    if prob.sol_status == pulp.LpSolutionOptimal:
        return "Optimal"
    if prob.sol_status == pulp.LpSolutionIntegerFeasible:
        return "Feasible (limit reached)"
    return pulp.LpSolution.get(prob.sol_status, "Unknown")


def check_optimal(prob: pulp.LpProblem, allow_feasible: bool = False) -> str:
    status = solution_status(prob)
    if status == "Optimal" or (allow_feasible and status.startswith("Feasible")):
        return status
    raise RuntimeError(f"{prob.name}: solver status {status}")
