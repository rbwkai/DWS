"""The renderer: turns a checked story into text. It never changes an action or an answer."""
from __future__ import annotations

import random
import re

from dwsbench.core.types import Instance, Rendered, Trace
from dwsbench.ops import REGISTRY

QUESTIONS = {"where": "Where is the {target} now?"}


def render(instance: Instance, trace: Trace, rng: random.Random) -> Rendered:
    names = set(instance.universe.items) | set(instance.universe.places)
    sentences = []
    for step in trace.steps:
        op = REGISTRY[step.event.op]
        sentence = rng.choice(op.templates).format(**op.words(step))
        if step.event.op == "narrate" and names & set(re.findall(r"[a-z]+", sentence.lower())):
            raise ValueError(f"filler sentence mentions an item or place: {sentence!r}")
        sentences.append(sentence)
    story = " ".join(sentences)
    question = QUESTIONS[instance.query].format(target=instance.target)
    return Rendered(story, question, len(story.split()), tuple(sentences))
