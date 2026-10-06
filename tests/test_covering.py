from itertools import combinations

import numpy as np
import pytest

from orpaper.models.covering import (coverage_sets, maximal_covering, nearest_open,
                                     ride_radius_km, set_covering)


def test_ride_radius():
    # 15 km/h, 10 min promise, 4 min fixed -> 6 min riding -> 1.5 km
    assert ride_radius_km(10, 15, 4) == pytest.approx(1.5)
    assert ride_radius_km(3, 15, 4) == 0.0


def test_set_covering_line():
    # demand at 0..4 on a line, sites at same points, radius 1 -> sites {1, 3} or {1, 4}... min 2
    pts = np.arange(5)
    dist = np.abs(pts[:, None] - pts[None, :])
    r = set_covering(coverage_sets(dist, 1))
    assert len(r.open_sites) == 2
    assert r.covered.all()


def test_set_covering_reports_uncoverable():
    cover = np.array([[1, 0], [0, 0], [0, 1]], bool)
    r = set_covering(cover)
    assert r.uncoverable == [1]
    assert sorted(r.open_sites) == [0, 1]


@pytest.mark.parametrize("seed", [0, 1])
def test_mclp_matches_brute_force(seed):
    rng = np.random.default_rng(seed)
    cover = rng.random((12, 6)) < 0.3
    w = rng.integers(1, 100, 12)
    best = max(w[cover[:, list(s)].any(axis=1)].sum() for s in combinations(range(6), 2))
    r = maximal_covering(cover, w, p=2)
    assert len(r.open_sites) == 2
    assert w[r.covered].sum() == pytest.approx(best)


def test_nearest_open():
    dist = np.array([[1.0, 5.0, 2.0], [4.0, 1.0, 3.0]])
    site, d = nearest_open(dist, [0, 2])
    assert site.tolist() == [0, 2]
    assert d.tolist() == [1.0, 3.0]
