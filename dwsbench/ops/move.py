from __future__ import annotations

from dwsbench.ops.base import Op

_MISSING = object()


class Move(Op):
    name = "move"
    arg_names = ("item", "place")
    templates = (
        "The {item} is moved from the {src} to the {dst}.",
        "Someone moves the {item} from the {src} to the {dst}.",
        "The {item} is taken from the {src} and brought to the {dst}.",
    )

    def problems(self, tl, args):
        bad = self.arg_problems(args)
        if bad:
            return bad
        current = tl.world.place_of.get(args["item"], _MISSING)
        if current is _MISSING:
            return [f"unknown item {args['item']!r}"]
        if current is None:
            return [f"{args['item']!r} is not placed yet"]
        if current == args["place"]:
            return [f"{args['item']!r} is already in {current!r}"]
        return []

    def apply(self, tl, args):
        return tl.push(tl.world.with_place(args["item"], args["place"]))

    def options(self, tl, universe):
        return [
            {"item": i, "place": p}
            for i in universe.items if tl.world.place_of.get(i) is not None
            for p in universe.places if p != tl.world.place_of[i]
        ]

    def words(self, step):
        item = step.event.args["item"]
        return {"item": item, "src": step.before.place_of[item], "dst": step.event.args["place"]}
