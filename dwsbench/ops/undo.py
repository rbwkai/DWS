from __future__ import annotations

from dwsbench.ops.base import Op


class Undo(Op):
    name = "undo"
    templates = (
        "The last change is undone.",
        "The most recent change is reversed.",
        "The latest change is taken back.",
    )

    def problems(self, tl, args):
        bad = self.arg_problems(args)
        if bad:
            return bad
        return [] if tl.can_back else ["nothing to undo"]

    def apply(self, tl, args):
        return tl.back()

    def options(self, tl, universe):
        return [{}] if tl.can_back else []
