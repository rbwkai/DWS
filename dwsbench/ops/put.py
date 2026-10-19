from __future__ import annotations

from dwsbench.ops.base import Op


class Put(Op):
    name = "put"
    arg_names = ("item", "place")
    templates = (
        "The {item} is in the {place}.",
        "The {item} starts out in the {place}.",
        "At the beginning, the {item} is in the {place}.",
    )

    def problems(self, tl, args):
        bad = self.arg_problems(args)
        if bad:
            return bad
        if args["item"] not in tl.world.place_of:
            return [f"unknown item {args['item']!r}"]
        if tl.world.place_of[args["item"]] is not None:
            return [f"{args['item']!r} is already placed"]
        return []

    def apply(self, tl, args):
        return tl.push(tl.world.with_place(args["item"], args["place"]))

    def options(self, tl, universe):
        return [
            {"item": i, "place": p}
            for i in universe.items if tl.world.place_of.get(i) is None
            for p in universe.places
        ]

    def words(self, step):
        return {"item": step.event.args["item"], "place": step.event.args["place"]}
