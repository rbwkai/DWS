"""Extra guards: planner, generator, validator, renderer, word lists."""
import dataclasses
import re

import pytest

from dwsbench.core.runner import run
from dwsbench.core.seeds import seed_for, stream
from dwsbench.core.types import Event, Failure, Instance, QuerySpec
from dwsbench.gen import generate
from dwsbench.gen.wordlists import ITEMS, PLACES
from dwsbench.ops import REGISTRY
from dwsbench.plan import PlanError, plan
from dwsbench.render import render
from dwsbench.validate import validate


# ---- planner
def cfg(**over):
    exp = {"vary": {"T": [2, 4]}, "fixed": {"E": 3, "places": 4, "D": 0, "V": 0, "N": 0}, "stories_per_cell": 5}
    exp.update(over)
    return {"experiments": {"x": exp}}


def test_planner_is_fixed_order_with_fixed_ids():
    out = plan(cfg())
    assert [p.spec.spec_id for p in out] == ["x/T02", "x/T04"]
    assert out == plan(cfg()) and all(p.stories == 5 for p in out)


def test_planner_refuses_impossible_orders():
    for fixed in ({"E": 3, "places": 4, "D": 0, "V": 3, "N": 0},      # V > T (T=2)
                  {"E": 1, "places": 4, "D": 2, "V": 0, "N": 0},      # D>0 needs E>=2
                  {"E": 3, "places": 1, "D": 0, "V": 0, "N": 0}):     # places < 2
        with pytest.raises(PlanError):
            plan(cfg(fixed=fixed))
    with pytest.raises(PlanError):
        plan(cfg(fixed={"E": 3, "places": 4, "D": 0, "V": 0}))          # N missing
    with pytest.raises(PlanError):
        plan(cfg(vary={"T": [2.5]}))                                   # exact whole numbers only


# ---- generator
SPEC = QuerySpec("t/spec", E=3, places=4, T=6, D=3, V=2, N=2)


def test_generator_is_deterministic_and_validates():
    results = [generate(SPEC, seed_for(1, i)) for i in range(40)]
    built = [r for r in results if isinstance(r, Instance)]
    assert len(built) > 10
    assert built == [r for r in [generate(SPEC, seed_for(1, i)) for i in range(40)] if isinstance(r, Instance)]
    assert all(validate(r, SPEC).ok for r in built)


def test_unbuildable_orders_report_failure():
    bad = QuerySpec("t/bad", E=2, places=2, T=2, D=0, V=0, N=0)  # target must bounce A->B->A: always boring
    assert all(isinstance(generate(bad, seed_for(2, i)), Failure) for i in range(30))


# ---- validator catches tampering
def one_instance():
    for i in range(100):
        inst = generate(SPEC, seed_for(3, i))
        if isinstance(inst, Instance):
            return inst
    raise AssertionError("no instance")


def test_validator_catches_tampering():
    inst = one_instance()
    assert validate(inst, SPEC).ok
    wrong_spec = dataclasses.replace(SPEC, D=SPEC.D + 1)
    assert not validate(inst, wrong_spec).ok
    assert not validate(dataclasses.replace(inst, body=inst.body[:-1]), SPEC).ok
    assert not validate(dataclasses.replace(inst, gold="nowhere"), SPEC).ok
    assert not validate(dataclasses.replace(inst, body=inst.body + (Event("remove", {"item": "x"}),)), SPEC).ok
    assert not validate(dataclasses.replace(inst, setup=inst.setup[:-1]), SPEC).ok
    assert not validate(dataclasses.replace(inst, body=(Event("put", {"item": inst.target, "place": "x"}),) + inst.body), SPEC).ok


# ---- renderer
def test_render_never_changes_the_story_only_the_words():
    inst = one_instance()
    trace = run(inst.universe, inst.setup, inst.body)
    a, b = render(inst, trace, stream(1, "render")), render(inst, trace, stream(2, "render"))
    assert a == render(inst, trace, stream(1, "render"))
    assert len(a.sentences) == len(b.sentences) == len(trace.steps)
    assert a.L == len(a.story.split()) and a.question == f"Where is the {inst.target} now?"


def test_undo_redo_and_filler_name_nothing():
    inst = one_instance()
    trace = run(inst.universe, inst.setup, inst.body)
    r = render(inst, trace, stream(5, "render"))
    names = set(inst.universe.items) | set(inst.universe.places)
    for step, sentence in zip(trace.steps, r.sentences):
        if step.event.op in ("undo", "redo", "narrate"):
            assert not names & set(re.findall(r"[a-z]+", sentence.lower()))


def test_word_lists_do_not_collide():
    names = set(ITEMS) | set(PLACES)
    assert len(ITEMS) == len(set(ITEMS)) and len(PLACES) == len(set(PLACES))
    assert not set(ITEMS) & set(PLACES)
    template_words = set()
    for op in REGISTRY.values():
        for t in op.templates:
            template_words |= set(re.findall(r"[a-z]+", re.sub(r"\{.*?\}", " ", t).lower()))
    assert not names & template_words, names & template_words
