"""Test 3: the counting example, checked by the validator end to end."""
from dwsbench.core.types import Instance, QuerySpec, Universe
from dwsbench.validate import validate
from tests.helpers import ev

UNI = Universe(("key", "cup"), ("desk", "shelf", "bag"))
SETUP = (ev("put", "key", "desk"), ev("put", "cup", "shelf"))
BODY = (ev("move", "key", "bag"), ev("move", "cup", "desk"), ev("narrate"),
        ev("move", "key", "shelf"), ev("undo"))
SPEC = QuerySpec("count/example", E=2, places=3, T=3, D=1, V=1, N=1)


def test_measured_numbers_and_answer():
    report = validate(Instance(UNI, "key", SETUP, BODY, "where", "bag"), SPEC)
    assert report.problems == ()
    assert report.ok
    m = report.measured
    assert (m.E, m.T, m.D, m.V, m.N) == (2, 3, 1, 1, 1)


def test_wrong_answer_is_caught():
    report = validate(Instance(UNI, "key", SETUP, BODY, "where", "shelf"), SPEC)
    assert not report.ok and any("saved answer" in p for p in report.problems)
