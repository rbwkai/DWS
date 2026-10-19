"""The shape every action has."""
from __future__ import annotations

from typing import Mapping

from dwsbench.core.types import Step, Timeline, Universe

Template = str  # a sentence pattern with {blanks}


class Op:
    name: str = ""
    arg_names: tuple[str, ...] = ()
    templates: tuple[Template, ...] = ()

    def arg_problems(self, args: Mapping[str, str]) -> list[str]:
        if set(args) != set(self.arg_names):
            return [f"{self.name} needs args {list(self.arg_names)}, got {sorted(args)}"]
        return []

    def problems(self, tl: Timeline, args: Mapping[str, str]) -> list[str]:
        """Empty list means the step is legal."""
        raise NotImplementedError

    def apply(self, tl: Timeline, args: Mapping[str, str]) -> Timeline:
        """Return a new timeline."""
        raise NotImplementedError

    def options(self, tl: Timeline, universe: Universe) -> list[dict]:
        """Every legal args right now."""
        raise NotImplementedError

    def words(self, step: Step) -> dict[str, str]:
        """Blanks to fill in the templates."""
        return {}
