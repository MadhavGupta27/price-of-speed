import numpy as np
import pytest

from orpaper.data.synthetic import transportation_instance
from orpaper.models.transportation import (northwest_corner, solve_transportation,
                                           vogel_approximation)


def test_balanced_2x2():
    r = solve_transportation([10, 10], [10, 10], [[1, 5], [5, 1]])
    assert r.cost == pytest.approx(20)
    np.testing.assert_allclose(r.flows, [[10, 0], [0, 10]])


def test_excess_supply_goes_to_dummy():
    r = solve_transportation([15, 10], [10, 10], [[1, 5], [5, 1]])
    assert r.cost == pytest.approx(20)
    assert r.unused_supply.sum() == pytest.approx(5)


def test_shortage_is_penalised():
    r = solve_transportation([5, 10], [10, 10], [[1, 5], [5, 1]], shortage_penalty=100)
    assert r.unmet_demand.sum() == pytest.approx(5)
    assert r.cost == pytest.approx(5 * 1 + 10 * 1 + 5 * 100)


def test_heuristics_feasible_and_not_better_than_lp():
    s, d, c = transportation_instance(4, 5, seed=1)
    opt = solve_transportation(s, d, c).cost
    for X in (northwest_corner(s, d), vogel_approximation(s, d, c)):
        np.testing.assert_allclose(X.sum(1), s)
        np.testing.assert_allclose(X.sum(0), d)
        assert (X * c).sum() >= opt - 1e-6
