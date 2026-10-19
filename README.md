# DWS-Bench v2: minimal core

A small program that makes test stories about a changing world, plus one question per story.

> The shoe is in the bin. The shoe is moved from the bin to the attic. The last change is undone.
> Where is the shoe now? -> bin

The right answer is always worked out by plain code (a simulator), never by a language model.
Same settings plus same seed always give the same file.

Version one: four actions (PUT, MOVE, UNDO, REDO) plus filler (NARRATE), one question ("where is the target?"),
and one straight path: settings -> plan -> generate -> check -> render -> save.

## Run

```bash
pip install -r requirements.txt
python -m dwsbench.build configs/core.yaml out/      # writes out/dataset.jsonl and out/manifest.json
python -m dwsbench.build configs/smoke.yaml out/     # one order, ten stories
python -m pytest                                     # all seven spec tests plus a few extra guards
```

## Layout

```
dwsbench/
  core/       types.py (every shared data shape), seeds.py, runner.py
  ops/        put.py move.py undo.py redo.py narrate.py  (+ base.py, registry in __init__.py)
  plan/       planner.py       settings -> QuerySpecs
  gen/        generator.py, wordlists.py
  validate/   measure.py, validator.py    re-checks a story from scratch
  render/     renderer.py      events -> text
  build.py    the only file that connects everything and writes the output
configs/      core.yaml, smoke.yaml
tests/
```

**The rule:** `plan`, `gen`, `validate` and `render` never import each other. They only use `core` and `ops`.
Only `build.py` uses all of them. `tests/test_7_folder_rule.py` fails if this is broken.

Adding an action later = add one file in `ops/` and register it in `ops/__init__.py`.

## The numbers (body only; setup is not counted)

| Name | Meaning |
| --- | --- |
| E | items in the world (PUTs in the setup) |
| T | body steps after which the target's place differs |
| D | body steps that change another item and leave the target alone |
| V | UNDO and REDO steps (counted inside T; each must act on the target) |
| N | filler steps that change nothing |
| L | word count of the story (recorded only) |

All are measured by comparing the world before and after each step, never from labels.

## Settings file

```yaml
root_seed: 20261018
max_attempts: 50
experiments:
  rq1:
    vary:  { T: [2, 4, 6, 8, 12, 16] }
    fixed: { E: 3, places: 4, D: 0, V: 0, N: 0 }
    stories_per_cell: 50
```

Exact whole numbers only. The planner makes one order per combination of the `vary` values
(ids look like `rq1/T08`) and refuses impossible orders (V > T, D > 0 with E < 2, places < 2, T < 1) and repeated values in a `vary` list.
An order can still be unbuildable (for example T=2 with only 2 places always returns to the start);
`build.py` marks those in `manifest.json` under `not_buildable` and logs a warning.
Before building anything, `build.py` also refuses a `max_attempts` below 1, a `root_seed` that is not a whole number,
and an `E` or `places` larger than the word lists (50 items, 30 places).

## Output

`dataset.jsonl`, one story per line: `instance_id` (`<spec_id>/<story number>`), `spec`, `universe`, `target`,
`setup`, `body`, `query`, `gold`, `step_gold` (world after every event, setup then body), `measured`
(E, T, D, V, N, L), `story`, `question`, `sentences` (one per event, same order).

`manifest.json`: git commit, Python version, root seed, stories made and failed attempts per order,
not-buildable orders, validator rejections, and the sha256 of the dataset file.

## Notes on choices the spec left open

- One QuerySpec per cell of an experiment. `stories_per_cell` stories are built from it; the story
  number is the last part of `instance_id`. The planner returns `Planned(spec, stories)`.
- A story's seed is `seed_for(root, spec_id, story_number)`; each attempt uses `seed_for(story_seed, attempt)`.
  Streams "setup", "pick" and "render" come from `random.Random`. The manifest records the Python version.
- If any story of an order uses up all attempts, that order is marked not buildable and the rest of its
  stories are skipped. Stories already made stay in the file and are counted in the manifest.
- `target` is saved as its own field because the question text needs it.
- The validator also rejects: a PUT in the body, a non-PUT in the setup, an UNDO/REDO that does not
  change the target, a NARRATE that changes something, and a setup that does not PUT every item once.
- Sentence patterns: each action has two or three equivalent wordings; the "render" stream picks one.
  UNDO/REDO never name the item, and filler never mentions an item or place (checked at render time and in tests).

- In version one UNDO/REDO are only generated when they change the target, so a distractor move never sits
  between a target move and the UNDO that reverts it.

## Not built yet (on purpose)

REMOVE/SPLIT/MERGE/SWAP, more question kinds, length-matched groups, running and scoring models, setting ranges.
