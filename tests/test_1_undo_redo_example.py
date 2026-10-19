"""Test 1: the must-pass UNDO/REDO example from the spec."""
from dwsbench.core.runner import advance, begin, run
from dwsbench.core.types import Universe
from tests.helpers import ev

UNI = Universe(("key",), ("A", "B", "C"))
SETUP = (ev("put", "key", "A"),)
BODY = (ev("move", "key", "B"), ev("undo"), ev("move", "key", "C"), ev("undo"), ev("redo"))


def test_five_steps_end_in_c():
    trace = run(UNI, SETUP, BODY)
    assert trace.final.world.place_of["key"] == "C"
    assert trace.setup_steps[-1].pointer == 1 and trace.final.floor == 1
    body = trace.body_steps
    assert [s.after.place_of["key"] for s in body] == ["B", "A", "C", "A", "C"]
    assert [s.pointer for s in body] == [2, 1, 2, 1, 2]
    assert [len(trace.final.saved)] == [3]


def test_b_copy_is_gone_after_step_3():
    trace = run(UNI, SETUP, BODY)
    saved_places = [w.place_of["key"] for w in trace.final.saved]
    assert saved_places == [None, "A", "C"]  # no B anywhere


def test_floor_zero_would_also_work():
    tl = begin(UNI)
    for i, e in enumerate(SETUP + BODY):
        tl, _ = advance(UNI, tl, e, i)  # never sealed, so floor stays 0
    assert tl.floor == 0 and tl.world.place_of["key"] == "C"
