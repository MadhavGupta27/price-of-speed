"""One-way sensitivity analysis: vary one parameter at a time, record metrics.

    def evaluate(params) -> dict:   # e.g. {"cost": ..., "vehicles": ...}
        ...
    df = one_way(evaluate, base={"capacity": 20, "fleet": 3},
                 grid={"capacity": [15, 20, 25], "fleet": [2, 3, 4]})
    plot_one_way(df, metric="cost", out="results/sensitivity_cost.png")
"""

import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def one_way(evaluate, base: dict, grid: dict) -> pd.DataFrame:
    rows = []
    for param, values in grid.items():
        for v in values:
            params = {**base, param: v}
            t0 = time.perf_counter()
            try:
                metrics = evaluate(params)
                status = "ok"
            except Exception as e:  # infeasible settings are results too
                metrics, status = {}, f"error: {e}"
            rows.append({"param": param, "value": v, "is_base": v == base[param],
                         "solve_s": time.perf_counter() - t0, "status": status, **metrics})
    return pd.DataFrame(rows)


def plot_one_way(df: pd.DataFrame, metric: str, out: str | Path):
    params = list(df["param"].unique())
    fig, axes = plt.subplots(1, len(params), figsize=(4 * len(params), 3.2), squeeze=False)
    for ax, p in zip(axes[0], params):
        sub = df[df["param"] == p]
        ax.plot(sub["value"], sub[metric], marker="o")
        base = sub[sub["is_base"]]
        ax.scatter(base["value"], base[metric], color="crimson", zorder=3, label="base")
        ax.set_xlabel(p)
        ax.set_ylabel(metric)
        ax.grid(alpha=0.3)
    axes[0][0].legend()
    fig.tight_layout()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    plt.close(fig)
