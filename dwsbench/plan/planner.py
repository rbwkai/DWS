"""The planner: turns settings into story orders. It never picks actions."""
from __future__ import annotations

import itertools

from dwsbench.core.types import QUERY_KINDS, Planned, QuerySpec

_NUMBERS = ("E", "places", "T", "D", "V", "N")


class PlanError(ValueError):
    """The settings describe an impossible or malformed order."""


def plan(config: dict) -> list[Planned]:
    """Return orders in a fixed order with fixed ids. Same settings, same list."""
    experiments = config.get("experiments")
    if not isinstance(experiments, dict) or not experiments:
        raise PlanError("config needs a non-empty 'experiments' mapping")
    planned: list[Planned] = []
    for name, exp in experiments.items():
        if not isinstance(exp, dict):
            raise PlanError(f"{name}: an experiment must be a mapping with vary / fixed / stories_per_cell")
        vary, fixed = dict(exp.get("vary") or {}), dict(exp.get("fixed") or {})
        stories = exp.get("stories_per_cell")
        if not _is_int(stories) or stories < 1:
            raise PlanError(f"{name}: stories_per_cell must be a whole number >= 1")
        allowed = set(_NUMBERS) | {"query"}
        unknown = (set(vary) | set(fixed)) - allowed
        if unknown:
            raise PlanError(f"{name}: unknown settings {sorted(unknown)}")
        if set(vary) & set(fixed):
            raise PlanError(f"{name}: {sorted(set(vary) & set(fixed))} are both varied and fixed")
        missing = [k for k in _NUMBERS if k not in vary and k not in fixed]
        if missing:
            raise PlanError(f"{name}: missing settings {missing}")
        for key, values in vary.items():
            if not isinstance(values, list) or not values:
                raise PlanError(f"{name}: vary.{key} must be a non-empty list of exact numbers")
            if len({repr(v) for v in values}) != len(values):
                raise PlanError(f"{name}: vary.{key} repeats a value ({values}); every cell needs its own id")
        for combo in itertools.product(*vary.values()):
            values = {**fixed, **dict(zip(vary.keys(), combo))}
            for k in _NUMBERS:
                if not _is_int(values[k]) or values[k] < 0:
                    raise PlanError(f"{name}: {k}={values[k]!r} must be an exact whole number >= 0")
            spec_id = f"{name}/" + ("-".join(_cell_label(k, values[k]) for k in vary) if vary else "base")
            spec = QuerySpec(spec_id, **{k: values[k] for k in _NUMBERS}, query=values.get("query", "where"))
            _check(spec)
            planned.append(Planned(spec, stories))
    return planned


def _cell_label(key: str, value: object) -> str:
    """Part of an order id: T=8 gives 'T08'; a word such as query='where' gives 'query-where'."""
    return f"{key}{value:02d}" if _is_int(value) else f"{key}-{value}"


def _is_int(x: object) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def _check(spec: QuerySpec) -> None:
    for k in _NUMBERS:
        if not _is_int(getattr(spec, k)) or getattr(spec, k) < 0:
            raise PlanError(f"{spec.spec_id}: {k} must be a whole number >= 0")
    if spec.query not in QUERY_KINDS:
        raise PlanError(f"{spec.spec_id}: unknown query {spec.query!r}")
    if spec.E < 1:
        raise PlanError(f"{spec.spec_id}: E must be at least 1")
    if spec.T < 1:
        raise PlanError(f"{spec.spec_id}: T must be at least 1 (the target must change)")
    if spec.V > spec.T:
        raise PlanError(f"{spec.spec_id}: V ({spec.V}) cannot be bigger than T ({spec.T})")
    if spec.D > 0 and spec.E < 2:
        raise PlanError(f"{spec.spec_id}: D above 0 needs E of at least 2")
    if spec.places < 2:
        raise PlanError(f"{spec.spec_id}: places must be at least 2")
