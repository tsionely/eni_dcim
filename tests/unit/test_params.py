import pytest

from aigp.core.params import ParamSet


BASE = {"control": {"backend": "velocity", "velocity": {"max_speed_mps": 4.0}},
        "planner": {"commit": {"distance_m": 2.0}}}


def test_dot_access():
    p = ParamSet(BASE)
    assert p.get("control.velocity.max_speed_mps") == 4.0
    assert p["control.backend"] == "velocity"
    with pytest.raises(KeyError):
        p.get("control.nope")
    assert p.get("control.nope", default=None) is None


def test_flatten_unflatten_roundtrip():
    p = ParamSet(BASE)
    flat = p.flatten()
    assert flat["planner.commit.distance_m"] == 2.0
    assert ParamSet.unflatten(flat) == p


def test_patch_is_immutable_and_changes_hash():
    p = ParamSet(BASE)
    p2 = p.patch({"planner.commit.distance_m": 3.0})
    assert p.get("planner.commit.distance_m") == 2.0
    assert p2.get("planner.commit.distance_m") == 3.0
    assert p.hash != p2.hash
    assert p.patch({}) == p and p.patch({}).hash == p.hash


def test_save_load_roundtrip(tmp_path):
    p = ParamSet(BASE)
    path = tmp_path / "params.json"
    p.save(path)
    assert ParamSet.load(path) == p
    assert ParamSet.load(path).hash == p.hash
