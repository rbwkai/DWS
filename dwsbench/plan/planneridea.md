`planner.py` takes your experiment settings (a config dict) and turns them into a list of "story orders" (`Planned` objects). It checks that the settings make sense and never picks any actual actions. Same settings always give the same list with the same ids.

**What it does, step by step**

1. **Reads the config.** It needs a non-empty `experiments` dict. Each experiment has `vary` (settings that take several values), `fixed` (settings with one value), and `stories_per_cell` (how many stories to make per combination).

2. **Checks each experiment.**
   - `stories_per_cell` must be a whole number, at least 1.
   - Only known settings are allowed: `E, places, T, D, V, N, query`.
   - A setting can't be both varied and fixed.
   - Every number (`E, places, T, D, V, N`) must appear in either `vary` or `fixed`.
   - Each `vary` value must be a non-empty list with no repeated values (every cell needs its own id).

3. **Builds every combination.** It uses `itertools.product` over the `vary` lists (a grid). For each combo it merges `fixed` with the combo's values, and checks that all numbers are whole and >= 0.

4. **Makes an id for each cell.** For example `rq1/T08` (T=8). With several varied settings they are joined with dashes (`rq1/E04-T08`). With nothing varied the id is `rq1/base`. `_cell_label` pads numbers to two digits (`T08`), and words become `query-where`.

5. **Creates a `QuerySpec`** for each cell, runs `_check` on it, and wraps it with `stories_per_cell` in a `Planned`.

**The sanity rules in `_check`**

- `query` must be a known kind (only `"where"` for now).
- `E >= 1`: at least one item.
- `T >= 1`: the target must change at least once.
- `V <= T`: undo/redo steps are counted inside T, so they can't exceed it.
- `D > 0` needs `E >= 2`: distractor moves need some other item to move.
- `places >= 2`: an item needs somewhere else to go.

**Small helpers**

- `_is_int` accepts whole numbers but rejects `True`/`False` (since `bool` is a subclass of `int` in Python).
- `PlanError` is a `ValueError` raised for any bad setting, with a message naming the experiment.
