"""Small helpers shared by the tests."""
from __future__ import annotations

from dwsbench.core.types import Event, Instance, QuerySpec, Universe


def ev(op: str, item: str | None = None, place: str | None = None) -> Event:
    args = {} if item is None else {"item": item, "place": place}
    return Event(op, args)


def instance_from_record(record: dict) -> tuple[Instance, QuerySpec]:
    """Rebuild an Instance and its order from one dataset line (independent of build.py)."""
    events = lambda lst: tuple(Event(e["op"], e["args"]) for e in lst)
    uni = Universe(tuple(record["universe"]["items"]), tuple(record["universe"]["places"]))
    inst = Instance(uni, record["target"], events(record["setup"]), events(record["body"]),
                    record["query"], record["gold"])
    return inst, QuerySpec(**record["spec"])
