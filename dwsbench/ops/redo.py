from __future__ import annotations

from dwsbench.ops.base import Op


class Redo(Op):
    name = "redo"
    templates = (
        "The change that was just undone is done again.",
        "The change that was just undone is applied once more.",
        "The most recently undone change is restored.",
    )

    def problems(self, tl, args):
        bad = self.arg_problems(args)
        if bad:
            return bad
        return [] if tl.can_forward else ["nothing to redo"]

    def apply(self, tl, args):
        return tl.forward()

    def options(self, tl, universe):
        return [{}] if tl.can_forward else []
