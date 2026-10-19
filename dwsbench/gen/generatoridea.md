`generator.py` builds the actions for one story from one order (`QuerySpec`). It returns an `Instance` if it works, or a `Failure` if it gets stuck. The caller can then retry with a new seed. Same spec and seed always give the same story.

## Step 1: pick names
- It makes two random streams from the seed: `setup` (names, starting places) and `pick` (body choices). Keeping them separate means changing how body steps are picked doesn't change the names or the start.
- It samples `E` items and `places` places without repeats, then picks one item as the **target**.
- If the word lists are too short, it returns a `Failure`.

## Step 2: write the setup
- It starts with an empty world and does one `put` per item to a random place. Items can share a place, because places are chosen with replacement.
- Each event goes through `advance`, which returns the new timeline and a `Step`.
- `seal` then sets the undo floor, so the story can never undo the setup.
- It remembers `start_place`, the target's place after setup.

## Step 3: the to-do list
```
target_move = T - V   (V is counted inside T, so subtract it)
other_move  = D
undo_redo   = V
filler      = N
```

## Step 4: fill the body (the core)
The loop runs exactly as many times as the to-do list totals, so T, D, V and N always come out exact. Each round:

1. **Dry-run every legal action.** For each kind that still has steps left, it asks the ops for all legal options and actually runs each one with `advance`. This shows which items would change. `_tried` caches this per round, because `move` is shared by `target_move` and `other_move`, so it only runs once.
2. **Filter by what each kind needs** (`_accepts`):
   - `target_move` and `undo_redo`: the **target must change**.
   - `other_move`: something changes, but **not the target** (a true distractor).
   - `filler` (`narrate`): always fine.
3. **Stuck check.** If no kind has any legal option, it returns `Failure("stuck ...")`.
4. **Pick a kind, weighted by how many are left.** Kinds with more remaining get picked more often, which mixes the story evenly.
5. **Pick a random option of that kind and commit it.** It updates the timeline, appends the event, and decrements the count.

The cache is cleared every round because the timeline changed, so old results no longer apply.

**Weak spot:** this is greedy with no backtracking. For example, if the only kinds left are `undo_redo` but nothing can be undone or redone in a way that changes the target, it fails instead of rewinding. That is why the caller retries with other seeds.

## Step 5: the answer
`gold` is the target's place in the final world. It comes from actually running the story, not from a formula, so it can't disagree with the events.

## Step 6: reject boring stories
> apperantly 40% of generated stories are boring, which allows "print starting point" heuristic; skipped by intend; -rbwkai

If `gold == start_place`, the reader wouldn't have had to track anything, so it returns `Failure("boring ...")`. This also catches a target that moves away and comes back, or an undo that returns it to the start.

Finally it returns `Instance(universe, target, setup, body, query, gold)`.
