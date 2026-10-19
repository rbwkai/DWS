understand the base.py.

each type of operations has some functions:
- problems: the reasons this op is NOT allowed right now (an empty list means it is allowed)
- apply: returns the NEW timeline; the old one is never changed
- options: every legal `args` dict this op could take right now. The generator picks its next step from these
- words: the *blanks* to be filled up in rendering
