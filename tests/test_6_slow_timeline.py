"""Test 6: a slow, obvious two-list timeline must agree with the real one."""
import random

from dwsbench.core.runner import advance, begin, seal, IllegalStep
from dwsbench.core.types import Event, Universe
from dwsbench.ops import REGISTRY

UNI = Universe(("a", "b", "c"), ("X", "Y", "Z"))


class SlowTimeline:
    """Current world plus one list for undo and one for redo. No pointer, no saved tuple."""

    def __init__(self, items):
        self.current = dict.fromkeys(items)
        self.undo_list, self.redo_list = [], []

    def seal(self):
        self.undo_list = []

    def legal(self, op, args):
        if op == "put":
            return self.current[args["item"]] is None
        if op == "move":
            return self.current[args["item"]] is not None and self.current[args["item"]] != args["place"]
        if op == "undo":
            return bool(self.undo_list)
        if op == "redo":
            return bool(self.redo_list)
        return True  # narrate

    def apply(self, op, args):
        if op in ("put", "move"):
            self.undo_list.append(dict(self.current))
            self.current[args["item"]] = args["place"]
            self.redo_list = []
        elif op == "undo":
            self.redo_list.append(dict(self.current))
            self.current = self.undo_list.pop()
        elif op == "redo":
            self.undo_list.append(dict(self.current))
            self.current = self.redo_list.pop()


def random_event(rng):
    op = rng.choice(["put", "move", "move", "undo", "undo", "redo", "narrate"])
    if op in ("put", "move"):
        return Event(op, {"item": rng.choice(UNI.items), "place": rng.choice(UNI.places)})
    return Event(op, {})


def test_slow_and_real_agree_on_thousands_of_random_lists():
    rng = random.Random(2026)
    compared = 0
    for _ in range(3000):
        real, slow = begin(UNI), SlowTimeline(UNI.items)
        # random setup, then seal both
        for item in UNI.items:
            if rng.random() < 0.7:
                e = Event("put", {"item": item, "place": rng.choice(UNI.places)})
                real, _ = advance(UNI, real, e)
                slow.apply("put", e.args)
        real = seal(real)
        slow.seal()
        for _ in range(rng.randint(1, 25)):
            e = random_event(rng)
            real_legal = not REGISTRY[e.op].problems(real, e.args)
            assert real_legal == slow.legal(e.op, e.args), (e, real)
            compared += 1
            if real_legal:
                real, _ = advance(UNI, real, e)
                slow.apply(e.op, e.args)
                assert dict(real.world.place_of) == slow.current
                assert real.can_back == bool(slow.undo_list)
                assert real.can_forward == bool(slow.redo_list)
            else:
                try:
                    advance(UNI, real, e)
                except IllegalStep:
                    pass
                else:
                    raise AssertionError("illegal step was not rejected")
    assert compared > 20000
