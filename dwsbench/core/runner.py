"""The runner: plays events on a timeline and records what happened.

Generator and validator both use this code. Test 6 guards against a bug here.
"""
from __future__ import annotations

from dwsbench.core.types import Event, Step, Timeline, Trace, Universe, World
from dwsbench.ops import REGISTRY


class IllegalStep(Exception):
    def __init__(self, index: int, event: Event, problems: list[str]):
        self.index, self.event, self.problems = index, event, problems
        super().__init__(f"step {index} ({event.op} {dict(event.args)}): " + "; ".join(problems))


def begin(universe: Universe) -> Timeline:
    """A timeline whose only saved copy is the empty world."""
    return Timeline.initial(World.empty(universe.items))


def seal(tl: Timeline) -> Timeline:
    """Set the floor right after the setup."""
    return tl.sealed()


def advance(universe: Universe, tl: Timeline, event: Event, index: int = 0) -> tuple[Timeline, Step]:
    """Play one event. An illegal event raises IllegalStep. It is never skipped."""
    op = REGISTRY.get(event.op)
    if op is None:
        raise IllegalStep(index, event, [f"unknown action {event.op!r}"])
    problems = _name_problems(universe, event) + op.problems(tl, event.args)
    if problems:
        raise IllegalStep(index, event, problems)
    new_tl = op.apply(tl, event.args)
    step = Step(index, event, tl.world, new_tl.world, tl.world.diff(new_tl.world), new_tl.pointer)
    return new_tl, step


def run(universe: Universe, setup: tuple[Event, ...], body: tuple[Event, ...]) -> Trace:
    """Play the setup, set the floor, then play the body."""
    tl = begin(universe)
    steps: list[Step] = []
    for ev in setup:
        tl, step = advance(universe, tl, ev, len(steps))
        steps.append(step)
    tl = seal(tl)
    for ev in body:
        tl, step = advance(universe, tl, ev, len(steps))
        steps.append(step)
    return Trace(universe, tuple(steps), len(setup), tl)


def _name_problems(universe: Universe, event: Event) -> list[str]:
    problems = []
    item, place = event.args.get("item"), event.args.get("place")
    if item is not None and item not in universe.items:
        problems.append(f"item {item!r} is not in the universe")
    if place is not None and place not in universe.places:
        problems.append(f"place {place!r} is not in the universe")
    return problems
