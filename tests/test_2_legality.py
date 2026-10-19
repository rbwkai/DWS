"""Test 2: legality edge cases."""
import pytest

from dwsbench.core.runner import IllegalStep, run
from dwsbench.core.types import Universe
from tests.helpers import ev

UNI = Universe(("key", "cup"), ("A", "B", "C"))
SETUP = (ev("put", "key", "A"), ev("put", "cup", "B"))


def play(*body):
    return run(UNI, SETUP, tuple(body))


def test_undo_right_after_setup_is_rejected():
    with pytest.raises(IllegalStep):
        play(ev("undo"))


def test_redo_right_after_new_move_is_rejected():
    with pytest.raises(IllegalStep):
        play(ev("move", "key", "B"), ev("undo"), ev("move", "key", "C"), ev("redo"))


def test_redo_with_nothing_undone_is_rejected():
    with pytest.raises(IllegalStep):
        play(ev("move", "key", "B"), ev("redo"))


def test_undo_narrate_redo_works():
    t = play(ev("move", "key", "B"), ev("undo"), ev("narrate"), ev("redo"))
    assert t.final.world.place_of["key"] == "B"


def test_undo_undo_redo_redo_works():
    t = play(ev("move", "key", "B"), ev("move", "cup", "C"), ev("undo"), ev("undo"), ev("redo"), ev("redo"))
    assert t.final.world.place_of == {"key": "B", "cup": "C"}


def test_move_to_same_place_is_rejected():
    with pytest.raises(IllegalStep):
        play(ev("move", "key", "A"))


def test_put_on_placed_item_is_rejected():
    with pytest.raises(IllegalStep):
        play(ev("put", "key", "C"))


def test_move_unplaced_item_is_rejected():
    with pytest.raises(IllegalStep):
        run(UNI, (ev("put", "key", "A"),), (ev("move", "cup", "C"),))


def test_unknown_names_and_actions_are_rejected():
    with pytest.raises(IllegalStep):
        play(ev("move", "key", "Z"))
    with pytest.raises(IllegalStep):
        play(ev("move", "spoon", "A"))
    with pytest.raises(IllegalStep):
        play(ev("teleport"))


def test_undo_never_goes_below_the_floor():
    with pytest.raises(IllegalStep):
        play(ev("move", "key", "B"), ev("undo"), ev("undo"))
