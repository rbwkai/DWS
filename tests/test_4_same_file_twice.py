"""Test 4: same settings plus same seed give the same file."""
import hashlib
import os
import subprocess
import sys
from pathlib import Path

import yaml

from dwsbench.build import build

ROOT = Path(__file__).resolve().parent.parent
CONFIG = yaml.safe_load((ROOT / "configs" / "smoke.yaml").read_text())


def test_in_process_twice(tmp_path):
    m1, m2 = build(CONFIG, tmp_path / "a"), build(CONFIG, tmp_path / "b")
    assert m1["dataset_sha256"] == m2["dataset_sha256"]
    assert (tmp_path / "a" / "dataset.jsonl").read_bytes() == (tmp_path / "b" / "dataset.jsonl").read_bytes()
    assert m1["dataset_sha256"] == hashlib.sha256((tmp_path / "a" / "dataset.jsonl").read_bytes()).hexdigest()


def test_command_line_with_different_hash_seeds(tmp_path):
    hashes = []
    for i, hash_seed in enumerate(("1", "2")):
        out = tmp_path / f"cli{i}"
        env = {**os.environ, "PYTHONHASHSEED": hash_seed}
        subprocess.run([sys.executable, "-m", "dwsbench.build", str(ROOT / "configs" / "smoke.yaml"), str(out)],
                       cwd=ROOT, env=env, check=True, capture_output=True)
        hashes.append(hashlib.sha256((out / "dataset.jsonl").read_bytes()).hexdigest())
    assert hashes[0] == hashes[1]


def test_different_root_seed_changes_the_file(tmp_path):
    other = {**CONFIG, "root_seed": CONFIG["root_seed"] + 1}
    assert build(CONFIG, tmp_path / "a")["dataset_sha256"] != build(other, tmp_path / "b")["dataset_sha256"]
