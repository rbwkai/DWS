"""The generator: builds the actions for one story from one order."""
from __future__ import annotations

from dwsbench.core.runner import advance, begin, seal
from dwsbench.core.seeds import stream
from dwsbench.core.types import Event, Failure, Instance, QuerySpec, Universe
from dwsbench.gen.wordlists import ITEMS, PLACES
from dwsbench.ops import REGISTRY

# kind -> (actions whose options are tried, accepted when ...)
_KINDS = {
    "target_move": ("move",),
    "other_move": ("move",),
    "undo_redo": ("undo", "redo"),
    "filler": ("narrate",),
}


def _accepts(kind: str, changed: tuple[str, ...], target: str) -> bool:
    if kind in ("target_move", "undo_redo"):
        return target in changed
    if kind == "other_move":
        return bool(changed) and target not in changed
    return True  # filler


def _tried(universe, tl, op_name, cache):
    """Every legal option of one action, tried once: (event, new timeline, changed)."""
    if op_name not in cache:
        results = []
        for args in REGISTRY[op_name].options(tl, universe):
            event = Event(op_name, args)
            new_tl, step = advance(universe, tl, event)
            results.append((event, new_tl, step.changed))
        cache[op_name] = results
    return cache[op_name]


def generate(spec: QuerySpec, seed: int) -> Instance | Failure:
    """Build one story. `seed` is the attempt seed."""
    rng_setup, rng_pick = stream(seed, "setup"), stream(seed, "pick")

    # 1. pick names
    if spec.E > len(ITEMS) or spec.places > len(PLACES):
        return Failure("not enough names in the word lists")
    items = tuple(rng_setup.sample(ITEMS, spec.E))
    places = tuple(rng_setup.sample(PLACES, spec.places))
    universe = Universe(items, places)
    target = rng_setup.choice(items)

    # 2. write the setup
    tl = begin(universe)
    setup = []
    for item in items:
        event = Event("put", {"item": item, "place": rng_setup.choice(places)})
        tl, _ = advance(universe, tl, event)
        setup.append(event)
    tl = seal(tl)
    start_place = tl.world.place_of[target]

    # 3. to-do list of step kinds
    remaining = {
        "target_move": spec.T - spec.V,
        "other_move": spec.D,
        "undo_redo": spec.V,
        "filler": spec.N,
    }

    # 4. fill it one step at a time. understand this part thoroughly, @mounota and @prince.
    body = []
    for _ in range(sum(remaining.values())):
        cache: dict = {}
        options_by_kind = {}
        for kind, op_names in _KINDS.items():
            if remaining[kind] == 0:
                continue
            options = [
                (event, new_tl)
                for op_name in op_names
                for event, new_tl, changed in _tried(universe, tl, op_name, cache)
                if _accepts(kind, changed, target)
            ]
            if options:
                options_by_kind[kind] = options
        if not options_by_kind:
            left = {k: v for k, v in remaining.items() if v}
            return Failure(f"stuck: no legal step for the kinds still waiting {left}")
        kinds = list(options_by_kind)
        kind = rng_pick.choices(kinds, weights=[remaining[k] for k in kinds])[0]
        event, tl = rng_pick.choice(options_by_kind[kind])
        body.append(event)
        remaining[kind] -= 1

    # 5. the question: where is the target? The answer comes from running the story.
    gold = tl.world.place_of[target]

    # 6. reject boring stories: if the answer is the starting place, nobody had to track anything
    if gold == start_place:
        return Failure("boring: the answer equals the target's starting place")

    return Instance(universe, target, tuple(setup), tuple(body), spec.query, gold)
