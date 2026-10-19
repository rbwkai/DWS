
## Core principle
Nothing is mutated. Every change returns a new `World` or `Timeline`. That's why `@dataclass(frozen=True)` and `MappingProxyType` are everywhere, and why `__reduce__` and `__hash__` are overridden (a `mappingproxy` can't be pickled or hashed by default).

## The world model

**`_freeze`**: wraps a dict in a read-only `MappingProxyType`, so `place_of` and `args` can't be edited in place.

**`Universe`**: the fixed vocabulary for one story: the tuple of item names and the tuple of place names. It's the "what exists" list; the order is fixed so generation is reproducible.

**`World`**: a snapshot of where every item is right now (`item -> place`, `None` = not placed yet).
- `empty(items)`: all items unplaced.
- `with_place(item, place)`: returns a new World with one item moved.
- `diff(other)`: items whose place differs; this feeds `Step.changed`.
- `__hash__`: sorted-items hash so Worlds can be compared and put in sets (useful for validation and deduping).

**`Timeline`**: the undo/redo machine. It holds `saved` (a tuple of World snapshots, oldest first), `pointer` (the current snapshot), and `floor` (UNDO can't go below it).
- `world`: the current snapshot.
- `can_back` / `can_forward`: whether undo or redo is possible.
- `push(world)`: truncates any redo history after the pointer, then appends the new world (standard editor-style undo semantics).
- `back()` / `forward()`: move the pointer, raising `ValueError` if illegal.
- `sealed()`: sets `floor = pointer`. This is called after the setup phase, so the story can never "undo" the initial placements.

## Events and execution records

**`Event`**: one atomic story action: `op` is `put | move | undo | redo | narrate`, with `args` like `{"item": "key", "place": "B"}`. `narrate` is the filler (no state change).

**`Step`**: what the runner records for each played event: its index, the event, the `before`/`after` Worlds, which items `changed`, and the timeline `pointer` afterwards. It's a complete audit trail of one transition.

**`Trace`**: the full execution of a story: the `universe`, all `steps` (setup, then body), `n_setup` (the split point, exposed through `setup_steps` / `body_steps`), and the `final` Timeline.

## Planning and generation

**`QuerySpec`**: a "story order", i.e. the difficulty knobs for one kind of instance:
- `E`: number of items; `places`: number of places
- `T`: body steps that change the **target** item
- `D`: body steps that change **other** items (distractors)
- `V`: UNDO/REDO steps (counted inside `T`)
- `N`: filler sentences
- `spec_id` (e.g. `"rq1/T08"`) labels it; `query` is `"where"`, the only question type in v1.

**`Planned`**: a `QuerySpec` plus how many stories to produce from it.

**`Instance`**: one generated story before it's turned into text: the universe, the `target` item, `setup` and `body` event tuples, the `query`, and the `gold` answer (the correct place).

**`Failure`**: returned when the generator's attempt couldn't produce a valid story, with a `reason`. This lets the generator retry instead of raising exceptions.

## Validation and rendering

**`Measured`**: the actual E, T, D, V, N counted from a generated story, plus `L` (word count, filled in after rendering).

**`Report`**: the validator's verdict: `ok`, the `measured` values, and a tuple of `problems`. Comparing `Measured` against the `QuerySpec` is how you check a story really has the difficulty it was ordered with.

**`Rendered`**: the final text output: the `story`, the `question`, total word count `L`, and `sentences` (one per event, in event order, which keeps the text traceable back to the events).

## The pipeline these types describe

`QuerySpec` → `Planned` → generator → `Instance` (or `Failure`) → runner → `Trace` → validator → `Report` / `Measured` → renderer → `Rendered`.

One thing worth noting: `QUERY_KINDS = ("where",)` is deliberately a single-element tuple, so adding new question types later (e.g. "which items are in X") is a local change.
