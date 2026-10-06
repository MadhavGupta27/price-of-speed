from itertools import permutations

import numpy as np
import pytest

from orpaper.data.synthetic import vrp_instance
from orpaper.models.vrp import nearest_neighbour, solve_cvrp


def test_single_vehicle_equals_tsp_brute_force():
    _, q, dist = vrp_instance(5, seed=3)
    tsp = min(dist[0, p[0]] + sum(dist[p[k], p[k + 1]] for k in range(4)) + dist[p[-1], 0]
              for p in permutations(range(1, 6)))
    r = solve_cvrp(dist, q, capacity=10_000, n_vehicles=1)
    assert r.cost == pytest.approx(tsp)
    assert r.vehicles_used == 1


def test_routes_feasible_and_beat_heuristic():
    _, q, dist = vrp_instance(8, seed=7)
    cap = int(np.ceil(q.sum() / 3))
    r = solve_cvrp(dist, q, cap, n_vehicles=4)
    visited = sorted(c for route in r.routes for c in route[1:-1])
    assert visited == list(range(1, 9))
    assert all(q[route].sum() <= cap for route in r.routes)
    assert r.cost <= nearest_neighbour(dist, q, cap).cost + 1e-6
