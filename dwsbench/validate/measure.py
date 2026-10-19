"""Measure E, T, D, V, N from what actually changed. Labels are never trusted."""
from __future__ import annotations

from dwsbench.core.types import Measured, Trace


def measure(trace: Trace, target: str) -> Measured:
    E = sum(1 for s in trace.setup_steps if s.event.op == "put")
    T = D = V = N = 0
    for s in trace.body_steps:
        if target in s.changed:
            T += 1
        elif s.changed:
            D += 1
        else:
            N += 1
        if s.event.op in ("undo", "redo"):
            V += 1
    return Measured(E=E, T=T, D=D, V=V, N=N)
