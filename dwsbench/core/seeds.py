"""Repeatable randomness. Every seed comes from `seed_for`.
My buddy said it's a good idea doing it this way.
"""

from __future__ import annotations

import hashlib
import random


def seed_for(root_seed: int, *labels: object) -> int:
    """Hash the text of the inputs into one number."""
    text = "\x1f".join(str(x) for x in (root_seed, *labels))
    return int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")


def stream(attempt_seed: int, name: str) -> random.Random:
    """A named random stream ("setup", "pick" or "render") inside one attempt."""
    return random.Random(seed_for(attempt_seed, name))
