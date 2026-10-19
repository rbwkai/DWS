"""Guards added after the debugging run: each one failed (or crashed) before its fix."""
import copy
import dataclasses
import pickle

import pytest

from dwsbench.build import build_dataset
from dwsbench.core.types import Event, Instance, QuerySpec, Universe, World
from dwsbench.plan import PlanError, plan
from dwsbench.validate import validate
from tests.helpers import ev

BASE = {"E": 3, "places": 4, "D": 0, "V": 0, "N": 0}


def cfg(vary=None, fixed=None, stories=2, **top):
    exp = {"vary": {"T": [2, 4]} if vary is None else vary,
           "fixed": dict(BASE) if fixed is None else fixed,
           "stories_per_cell": stories}
    return {"experiments": {"x": exp}, **top}


# ---- planner
def test_repeated_vary_values_are_refused():
    with pytest.raises(PlanError):
        plan(cfg(vary={"T": [4, 4]}))          # two orders would share the id x/T04


def test_empty_experiment_is_a_plan_error_not_a_crash():
    with pytest.raises(PlanError):
        plan({"experiments": {"x": None}})


def test_query_can_be_varied_and_gets_a_word_label():
    out = plan(cfg(vary={"T": [2], "query": ["where"]}))
    assert [p.spec.spec_id for p in out] == ["x/T02-query-where"]


# ---- build settings
@pytest.mark.parametrize("bad", [0, -3, "5", 2.5, True])
def test_bad_max_attempts_is_refused(bad):
    with pytest.raises(ValueError):
        build_dataset(cfg(vary={"T": [4]}, max_attempts=bad))


def test_bad_root_seed_is_refused():
    with pytest.raises(ValueError):
        build_dataset(cfg(vary={"T": [4]}, root_seed="abc"))


def test_more_items_than_names_fails_early_not_after_all_attempts():
    with pytest.raises(ValueError, match="wordlists"):
        build_dataset(cfg(vary={"T": [4]}, fixed={**BASE, "E": 60}))


# ---- shared data shapes survive pickle / deepcopy / hashing
def test_world_and_event_pickle_copy_and_hash():
    w, e = World({"a": "X", "b": None}), Event("move", {"item": "a", "place": "Y"})
    for obj in (w, e):
        assert pickle.loads(pickle.dumps(obj)) == obj
        assert copy.deepcopy(obj) == obj
        assert hash(obj) == hash(copy.deepcopy(obj))
    assert len({w, World({"b": None, "a": "X"})}) == 1       # same content, same hash, one set member


def test_a_whole_instance_can_cross_a_process_boundary():
    uni = Universe(("key",), ("A", "B"))
    inst = Instance(uni, "key", (ev("put", "key", "A"),), (ev("move", "key", "B"),), "where", "B")
    assert pickle.loads(pickle.dumps(inst)) == inst


# ---- validator: malformed data is rejected, not a crash
def test_validator_rejects_non_text_args():
    uni = Universe(("key",), ("A", "B"))
    spec = QuerySpec("t", E=1, places=2, T=1, D=0, V=0, N=0)
    inst = Instance(uni, "key", (ev("put", "key", "A"),), (Event("move", {"item": ["key"], "place": "B"}),), "where", "B")
    report = validate(inst, spec)
    assert not report.ok and any("plain text" in p for p in report.problems)
