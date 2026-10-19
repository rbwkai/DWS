"""One file per action. Adding an action means adding a file and registering it here."""
from dwsbench.ops.move import Move
from dwsbench.ops.narrate import Narrate
from dwsbench.ops.put import Put
from dwsbench.ops.redo import Redo
from dwsbench.ops.undo import Undo

REGISTRY = {op.name: op for op in (Put(), Move(), Undo(), Redo(), Narrate())}
