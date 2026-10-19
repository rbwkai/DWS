"""The validator: re-checks a finished story from scratch.

It sees only the story and its order. It never imports generator code.
"""
from __future__ import annotations

from dwsbench.core.runner import IllegalStep, run
from dwsbench.core.types import QUERY_KINDS, Instance, QuerySpec, Report
from dwsbench.ops import REGISTRY
from dwsbench.validate.measure import measure

_BODY_OPS = ("move", "undo", "redo", "narrate")


def validate(instance: Instance, spec: QuerySpec) -> Report:
    problems: list[str] = []
    uni = instance.universe

    # 1. every action is known and its args are complete
    for where, events in (("setup", instance.setup), ("body", instance.body)):
        for i, ev in enumerate(events):
            op = REGISTRY.get(ev.op)
            if op is None:
                problems.append(f"{where}[{i}]: unknown action {ev.op!r}")
            elif set(ev.args) != set(op.arg_names):
                problems.append(f"{where}[{i}]: {ev.op} needs args {list(op.arg_names)}, got {sorted(ev.args)}")
            elif not all(isinstance(v, str) for v in ev.args.values()):
                problems.append(f"{where}[{i}]: {ev.op} args must be plain text, got {dict(ev.args)}")
            elif where == "setup" and ev.op != "put":
                problems.append(f"setup[{i}]: only put is allowed in the setup, got {ev.op!r}")
            elif where == "body" and ev.op not in _BODY_OPS:
                problems.append(f"body[{i}]: {ev.op!r} is not allowed in the body")
    if instance.target not in uni.items:
        problems.append(f"target {instance.target!r} is not an item")
    if instance.query not in QUERY_KINDS:
        problems.append(f"unknown query {instance.query!r}")
    if problems:
        return Report(False, None, tuple(problems))

    # 2. replay from scratch: every step must be legal
    try:
        trace = run(uni, instance.setup, instance.body)
    except IllegalStep as exc:
        return Report(False, None, (f"replay: {exc}",))

    # 3. measure from what actually changed
    measured = measure(trace, instance.target)

    # 4. each measured number must equal the order
    for name in ("E", "T", "D", "V", "N"):
        got, wanted = getattr(measured, name), getattr(spec, name)
        if got != wanted:
            problems.append(f"measured {name}={got} but the order says {wanted}")
    if len(uni.items) != spec.E:
        problems.append(f"universe has {len(uni.items)} items but E={spec.E}")
    if len(uni.places) != spec.places:
        problems.append(f"universe has {len(uni.places)} places but the order says {spec.places}")
    if instance.query != spec.query:
        problems.append(f"query {instance.query!r} differs from the order's {spec.query!r}")

    # 5. extra rules
    put_items = [ev.args["item"] for ev in instance.setup]
    if sorted(put_items) != sorted(uni.items):
        problems.append("the setup must PUT every item exactly once")
    for step in trace.body_steps:
        op = step.event.op
        if op in ("move", "undo", "redo") and not step.changed:
            problems.append(f"step {step.index}: {op} changed nothing")
        if op == "narrate" and step.changed:
            problems.append(f"step {step.index}: narrate changed something")
        if op in ("undo", "redo") and instance.target not in step.changed:
            problems.append(f"step {step.index}: {op} did not act on the target (version one needs it to)")
    final_place = trace.final.world.place_of[instance.target]
    if final_place is None:
        problems.append("the target is not placed at the end")
    if trace.n_setup:
        start_place = trace.setup_steps[-1].after.place_of[instance.target]
        if final_place == start_place:
            problems.append("the answer equals the target's starting place")
    if instance.gold != final_place:
        problems.append(f"saved answer {instance.gold!r} differs from the replay's {final_place!r}")

    return Report(not problems, measured, tuple(problems))
