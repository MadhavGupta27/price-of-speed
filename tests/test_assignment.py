from itertools import permutations

import numpy as np
import pytest

from orpaper.models.assignment import solve_assignment


def brute_force(c):
    n = len(c)
    return min(sum(c[i][p[i]] for i in range(n)) for p in permutations(range(n)))


@pytest.mark.parametrize("seed", [0, 1, 2])
def test_matches_brute_force(seed):
    c = np.random.default_rng(seed).integers(1, 50, (5, 5))
    assert solve_assignment(c).cost == pytest.approx(brute_force(c))


def test_forbidden_pairs_respected():
    c = [[1, 9], [9, 1]]
    r = solve_assignment(c, forbidden=[(0, 0)])
    assert (0, 0) not in r.pairs
    assert r.cost == 18


def test_capacity_allows_multiple_tasks():
    r = solve_assignment([[1, 1, 1], [9, 9, 9]], capacity=[3, 1])
    assert r.cost == 3


def test_insufficient_capacity_raises():
    with pytest.raises(ValueError):
        solve_assignment([[1, 2, 3]])
