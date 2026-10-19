"""Test 5: 1,000+ stories over a mix of settings all pass the validator."""
from dwsbench.build import build_dataset
from dwsbench.validate import validate
from tests.helpers import instance_from_record

CONFIG = {
    "root_seed": 7,
    "max_attempts": 100,
    "experiments": {
        "depth":    {"vary": {"T": [1, 2, 4, 8, 16]}, "fixed": {"E": 3, "places": 4, "D": 0, "V": 0, "N": 0}, "stories_per_cell": 70},
        "revision": {"vary": {"V": [0, 1, 2, 4]}, "fixed": {"E": 3, "places": 4, "T": 6, "D": 0, "N": 0}, "stories_per_cell": 70},
        "distract": {"vary": {"D": [0, 4, 16]}, "fixed": {"E": 4, "places": 5, "T": 4, "V": 0, "N": 0}, "stories_per_cell": 70},
        "filler":   {"vary": {"N": [0, 8]}, "fixed": {"E": 2, "places": 3, "T": 4, "D": 0, "V": 0}, "stories_per_cell": 70},
        "mixed":    {"vary": {"E": [2, 5]}, "fixed": {"places": 6, "T": 6, "D": 3, "V": 2, "N": 3}, "stories_per_cell": 70},
    },
}


def test_all_stories_validate_and_match_the_order():
    records, stats = build_dataset(CONFIG)
    assert len(records) >= 1000
    assert stats["not_buildable"] == {}
    assert stats["validator_rejections"] == 0
    for rec in records:
        inst, spec = instance_from_record(rec)
        report = validate(inst, spec)                      # re-check from the saved line alone
        assert report.ok, (rec["instance_id"], report.problems)
        m = rec["measured"]
        assert (m["E"], m["T"], m["D"], m["V"], m["N"]) == (spec.E, spec.T, spec.D, spec.V, spec.N)
        assert len(rec["sentences"]) == len(rec["setup"]) + len(rec["body"]) == len(rec["step_gold"])
        assert m["L"] == len(rec["story"].split())
        assert rec["step_gold"][-1][rec["target"]] == rec["gold"]
        assert rec["question"] == f"Where is the {rec['target']} now?"
