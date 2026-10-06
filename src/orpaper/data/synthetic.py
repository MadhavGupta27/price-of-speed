"""Seeded synthetic instance generators.

Use when real data is unavailable or to build toy -> scaled instances.
Parameter ranges are placeholders: justify the final ranges from the
literature or real data and record them in data/README.md.
"""

import numpy as np


def transportation_instance(m=3, n=4, seed=42, supply_range=(50, 150),
                            cost_range=(2, 20), balanced=True):
    rng = np.random.default_rng(seed)
    supply = rng.integers(*supply_range, size=m)
    demand = rng.multinomial(int(supply.sum()), np.ones(n) / n) if balanced \
        else rng.integers(*supply_range, size=n)
    cost = rng.integers(*cost_range, size=(m, n))
    return supply, demand, cost


def assignment_instance(m=5, n=5, seed=42, cost_range=(10, 100)):
    rng = np.random.default_rng(seed)
    return rng.integers(*cost_range, size=(m, n))


def euclidean_matrix(coords):
    coords = np.asarray(coords, float)
    diff = coords[:, None, :] - coords[None, :, :]
    return np.sqrt((diff ** 2).sum(-1))


def vrp_instance(n_customers=10, seed=42, grid=100, demand_range=(1, 10),
                 depot_at_centre=True):
    """Return coords (n+1, 2), demand (n+1,) with depot 0, and Euclidean distances."""
    rng = np.random.default_rng(seed)
    coords = rng.uniform(0, grid, size=(n_customers + 1, 2))
    if depot_at_centre:
        coords[0] = (grid / 2, grid / 2)
    demand = np.concatenate([[0], rng.integers(*demand_range, size=n_customers)])
    return coords, demand, euclidean_matrix(coords)


def project_network(n_activities=8, seed=42, max_preds=2, pert=True, crash=True):
    """Random acyclic activity network with optional PERT estimates and crash data."""
    rng = np.random.default_rng(seed)
    names = [chr(ord("A") + i) for i in range(n_activities)]
    acts = {}
    for i, name in enumerate(names):
        k = int(rng.integers(0, min(i, max_preds) + 1)) if i else 0
        pred = sorted(rng.choice(names[:i], size=k, replace=False).tolist()) if k else []
        m = int(rng.integers(2, 10))
        a, b = max(1, m - int(rng.integers(1, 3))), m + int(rng.integers(1, 5))
        act = {"pred": pred, "duration": m}
        if pert:
            act.update(a=a, m=m, b=b)
        if crash:
            act.update(crash_duration=max(1, m - int(rng.integers(0, 3))),
                       crash_cost_per_unit=int(rng.integers(50, 500)))
        acts[name] = act
    return acts
