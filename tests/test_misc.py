import pytest

from orpaper.config import load_config, search_string
from orpaper.data.osrm import haversine_matrix
from orpaper.data.synthetic import project_network
from orpaper.models.cpm_pert import cpm
from orpaper.sensitivity import one_way


def test_haversine_london_paris():
    d = haversine_matrix([(51.5074, -0.1278), (48.8566, 2.3522)])
    assert d[0, 1] == pytest.approx(344, abs=2)


def test_synthetic_project_is_acyclic_and_solvable():
    assert cpm(project_network(12, seed=5)).makespan > 0


def test_one_way_records_errors_as_rows():
    def evaluate(p):
        if p["x"] < 0:
            raise RuntimeError("infeasible")
        return {"y": p["x"] ** 2}
    df = one_way(evaluate, {"x": 1}, {"x": [-1, 1, 2]})
    assert df["status"].tolist()[0].startswith("error")
    assert df["y"].tolist()[1:] == [1, 4]


def test_config_loads_and_search_string_keeps_mandatory_terms():
    cfg = load_config()
    assert '"operations" AND "research"' in search_string(cfg)
