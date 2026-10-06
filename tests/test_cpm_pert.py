import pytest

from orpaper.models.cpm_pert import cpm, crash, pert, pert_estimates

ACTS = {
    "A": {"duration": 3, "pred": [], "crash_duration": 2, "crash_cost_per_unit": 100},
    "B": {"duration": 2, "pred": ["A"], "crash_duration": 1, "crash_cost_per_unit": 10},
    "C": {"duration": 4, "pred": ["A"], "crash_duration": 2, "crash_cost_per_unit": 50},
    "D": {"duration": 1, "pred": ["B", "C"], "crash_duration": 1, "crash_cost_per_unit": 0},
}


def test_cpm_textbook():
    r = cpm(ACTS)
    assert r.makespan == 8
    assert r.critical_path == ["A", "C", "D"]
    assert r.slack["B"] == 2


def test_pert_estimates():
    te, var = pert_estimates({"X": {"a": 2, "m": 5, "b": 14, "pred": []}})
    assert te["X"] == pytest.approx(6)
    assert var["X"] == pytest.approx(4)


def test_pert_probability_at_mean_is_half():
    acts = {"X": {"a": 2, "m": 5, "b": 14, "pred": []}}
    res, sigma, p = pert(acts, deadline=6)
    assert sigma == pytest.approx(2)
    assert p == pytest.approx(0.5)


def test_crash_no_reduction_needed():
    assert crash(ACTS, deadline=8).crash_cost == pytest.approx(0)


def test_crash_picks_cheapest_critical():
    # Need 2 units off: C at 50/unit is cheaper than A at 100/unit; B then becomes
    # critical at 6 but 3+2+1 = 6 still meets the deadline.
    r = crash(ACTS, deadline=6)
    assert r.crash_cost == pytest.approx(100)
    assert r.crashed_by == {"C": 2}
    assert r.makespan <= 6 + 1e-9
