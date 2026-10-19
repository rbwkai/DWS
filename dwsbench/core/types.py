"""All shared data shapes live here. Everything else depends on this file.

Nothing is ever edited in place: a change builds a new World or a new Timeline.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType
from typing import Mapping

QUERY_KINDS = ("where",)  # version one has a single kind of question


def _freeze(mapping: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(mapping))


# ---------------------------------------------------------------- the world
@dataclass(frozen=True)
class Universe:
    """The names that exist: items and places, in a fixed order"""
    items: tuple[str, ...]
    places: tuple[str, ...]


@dataclass(frozen=True)
class World:
    """Where every item is right now. None means 'not placed yet'."""
    place_of: Mapping[str, str | None]

    def __post_init__(self) -> None:
        object.__setattr__(self, "place_of", _freeze(self.place_of))

    def __reduce__(self):
        # a mappingproxy cannot be pickled or deep-copied; rebuild from a plain dict instead
        return (World, (dict(self.place_of),))

    def __hash__(self) -> int:
        return hash(tuple(sorted(self.place_of.items())))  # item names are unique, so places are never compared

    @classmethod
    def empty(cls, items: tuple[str, ...]) -> "World":
        return cls(dict.fromkeys(items))

    def with_place(self, item: str, place: str) -> "World":
        updated = dict(self.place_of)
        updated[item] = place
        return World(updated)

    def diff(self, other: "World") -> tuple[str, ...]:
        """Items whose place differs between this world and `other`."""
        return tuple(i for i, p in self.place_of.items() if other.place_of.get(i) != p)


@dataclass(frozen=True)
class Timeline:
    """Saved copies of the world, a pointer to the current one, and a floor."""
    saved: tuple[World, ...]   # oldest first
    pointer: int               # which saved copy is current
    floor: int                 # UNDO can never go below this

    @classmethod
    def initial(cls, world: World) -> "Timeline":
        return cls((world,), 0, 0)

    @property
    def world(self) -> World:
        return self.saved[self.pointer]

    @property
    def can_back(self) -> bool:
        return self.pointer > self.floor

    @property
    def can_forward(self) -> bool:
        return self.pointer < len(self.saved) - 1

    def push(self, world: World) -> "Timeline":
        """Keep saved[:pointer+1], add the new copy. Later copies are thrown away."""
        saved = self.saved[: self.pointer + 1] + (world,)
        return replace(self, saved=saved, pointer=self.pointer + 1)

    def back(self) -> "Timeline":
        if not self.can_back:
            raise ValueError("cannot go back past the floor")
        return replace(self, pointer=self.pointer - 1)

    def forward(self) -> "Timeline":
        if not self.can_forward:
            raise ValueError("nothing to go forward to")
        return replace(self, pointer=self.pointer + 1)

    def sealed(self) -> "Timeline":
        """Set the floor to the current pointer (done right after the setup)."""
        return replace(self, floor=self.pointer)


# ------------------------------------------------------------------ events
@dataclass(frozen=True)
class Event:
    op: str                      # "put" | "move" | "undo" | "redo" | "narrate"
    args: Mapping[str, str]      # {"item": "key", "place": "B"} or {}

    def __post_init__(self) -> None:
        object.__setattr__(self, "args", _freeze(self.args))

    def __reduce__(self):
        return (Event, (self.op, dict(self.args)))

    def __hash__(self) -> int:
        return hash((self.op, tuple(sorted(self.args.items()))))


@dataclass(frozen=True)
class Step:
    """One played event, recorded by the runner."""
    index: int                   # position in setup + body
    event: Event
    before: World
    after: World
    changed: tuple[str, ...]     # items whose place differs before vs after
    pointer: int                 # timeline pointer after the step


@dataclass(frozen=True)
class Trace:
    universe: Universe
    steps: tuple[Step, ...]      # setup steps followed by body steps
    n_setup: int
    final: Timeline

    @property
    def setup_steps(self) -> tuple[Step, ...]:
        return self.steps[: self.n_setup]

    @property
    def body_steps(self) -> tuple[Step, ...]:
        return self.steps[self.n_setup:]


# --------------------------------------------------- planner / generator I/O
@dataclass(frozen=True)
class QuerySpec:
    """One story order."""
    spec_id: str      # for example "rq1/T08"
    E: int            # items in the world
    places: int       # how many places exist
    T: int            # body steps that change the target
    D: int            # body steps that change other items
    V: int            # UNDO or REDO steps (counted inside T)
    N: int            # filler sentences
    query: str = "where"


@dataclass(frozen=True)
class Planned:
    """A QuerySpec plus how many stories to make from it."""
    spec: QuerySpec
    stories: int


@dataclass(frozen=True)
class Instance:
    """One generated story, before rendering."""
    universe: Universe
    target: str
    setup: tuple[Event, ...]
    body: tuple[Event, ...]
    query: str
    gold: str


@dataclass(frozen=True)
class Failure:
    """The generator could not build a story from this attempt."""
    reason: str


@dataclass(frozen=True)
class Measured:
    E: int
    T: int
    D: int
    V: int
    N: int
    L: int | None = None   # word count, filled in after rendering


@dataclass(frozen=True)
class Report:
    ok: bool
    measured: Measured | None
    problems: tuple[str, ...]


@dataclass(frozen=True)
class Rendered:
    story: str
    question: str
    L: int
    sentences: tuple[str, ...]   # one per event, same order as the events
