from itertools import combinations

import numpy as np
import pytest

from orpaper.models.design import rider_cost_matrix, solve_design


def brute_force(d, r, C, F):
    n, m = d.shape
    best = np.inf
    for k in range(1, m + 1):
        for S in combinations(range(m), k):
            cost = F * k
            for i in range(n):
                opts = [C[i, j] for j in S if d[i, j] <= r]
                if not opts:
                    break
                cost += min(opts)
            else:
                best = min(best, cost)
    return best


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    d = rng.uniform(0, 5, (8, 5))
    C = d * 10
    r = 3.5
    if not (d <= r).any(axis=1).all():
        pytest.skip("instance has unreachable cells")
    res = solve_design(d, r, C, fixed_cost=15)
    assert res.unserved_cells == []
    assert res.store_cost + res.rider_cost == pytest.approx(brute_force(d, r, C, 15))


def test_unreachable_cells_reported_not_infeasible():
    d = np.array([[1.0, 9.0], [9.0, 9.0]])
    res = solve_design(d, 2.0, d, fixed_cost=1)
    assert res.unserved_cells == [1]
    assert res.open_sites == [0]


def test_rider_cost_matrix_units():
    # 1 order/day, 1.5 km at 15 km/h -> 0.2 h round trip, no handover, util 1, INR 100/h, 30 days
    c = rider_cost_matrix(np.array([[1.5]]), np.array([1.0]), 15, 0, 1.0, 100)
    assert c[0, 0] == pytest.approx(0.2 * 100 * 30)
