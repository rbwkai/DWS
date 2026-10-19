# whats going on..
Project generates custom story with gold answer. 4 operations currently: put, move, undo, redo.

### how?
1. `core` contains the structs:
    - Universe: list of all objects and places
    - World: a single snapshot of the state
    - Timeline: think as a list of worlds and a pointer to the current one. *@rbwkai put some CP ideas together to implement redo and undo.*

2. `plan`: turns the settings into one order (QuerySpec) per experiment cell; `stories_per_cell` stories are then built from each order
3. `gen`: generates symbolic sequences of operations
4. `validate`: re-plays and re-checks every story from scratch. (written mostly by AI and less rigorously supervised)
5. `render`: makes english story from symbolic operations from gen.

I've added notes and comments where I think its needed.. start reading them in the order mentioned above.
    
### the undo redo hack
- a `world` is a map of *object -> where the object is*
- a `timeline` is a sequence of `world`s
- lets say we have a *pointer* at the latest `world` of the timeline
- `undo`? move the pointer 1 step back
- `redo`? (if possible) move the pointer one step forward
- doing a general operation erases everything from that point on in (redo) direction.
- the *floor*: right after the setup the pointer position is remembered, and `undo` can never go below it (the starting PUTs can't be undone)
- version one only writes an `undo`/`redo` that changes the *target* item
- you're welcome.