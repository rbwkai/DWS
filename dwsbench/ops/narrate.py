from __future__ import annotations

from dwsbench.ops.base import Op


class Narrate(Op):
    """Filler. Changes nothing. Sentences must never mention an item or a place."""
    name = "narrate"
    templates = (
        "The room is quiet.",
        "It is a calm afternoon.",
        "Nothing else seems to happen for a while.",
        "A clock ticks somewhere nearby.",
        "The lights hum softly.",
        "Someone walks by without stopping.",
        "The air feels still.",
        "A faint breeze passes through.",
        "Time passes slowly.",
        "Everything is calm for a moment.",
    )

    def problems(self, tl, args):
        return self.arg_problems(args)

    def apply(self, tl, args):
        return tl

    def options(self, tl, universe):
        return [{}]
