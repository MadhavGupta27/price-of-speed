import pulp


def get_solver(name: str = "HiGHS", time_limit_s: float | None = None, msg: bool = False):
    """Return a PuLP solver. HiGHS ships via `highspy`; CBC ships with PuLP 2.x."""
    if name == "HiGHS":
        return pulp.HiGHS(msg=msg, timeLimit=time_limit_s)
    if name == "PULP_CBC_CMD":
        return pulp.PULP_CBC_CMD(msg=msg, timeLimit=time_limit_s)
    raise ValueError(f"Unknown solver {name!r}")


def check_optimal(prob: pulp.LpProblem) -> None:
    status = pulp.LpStatus[prob.status]
    if status != "Optimal":
        raise RuntimeError(f"{prob.name}: solver status {status}")
