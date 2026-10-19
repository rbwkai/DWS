"""build.py: the only file that connects the stages and writes the output.

    python -m dwsbench.build configs/core.yaml out/
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import platform
import subprocess
import sys
from pathlib import Path

from dwsbench.core.runner import run
from dwsbench.core.seeds import seed_for, stream
from dwsbench.core.types import Event, Failure
from dwsbench.gen import generate
from dwsbench.gen.wordlists import ITEMS, PLACES
from dwsbench.plan import plan
from dwsbench.render import render
from dwsbench.validate import validate

log = logging.getLogger("dwsbench")

DEFAULT_MAX_ATTEMPTS = 50


def _events(events) -> list[dict]:
    return [{"op": e.op, "args": dict(e.args)} for e in events]


def _record(instance_id, spec, instance, trace, rendered, measured) -> dict:
    return {
        "instance_id": instance_id,
        "spec": dataclasses.asdict(spec),
        "universe": {"items": list(instance.universe.items), "places": list(instance.universe.places)},
        "target": instance.target,
        "setup": _events(instance.setup),
        "body": _events(instance.body),
        "query": instance.query,
        "gold": instance.gold,
        "step_gold": [dict(step.after.place_of) for step in trace.steps],
        "measured": dataclasses.asdict(dataclasses.replace(measured, L=rendered.L)),
        "story": rendered.story,
        "question": rendered.question,
        "sentences": list(rendered.sentences),
    }


def _check_run_settings(config: dict, orders) -> None:
    """Fail early, with a clear message, on settings that would only fail late and confusingly."""
    seed, attempts = config.get("root_seed", 0), config.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError(f"root_seed must be a whole number, got {seed!r}")
    if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
        raise ValueError(f"max_attempts must be a whole number >= 1, got {attempts!r}")
    for planned in orders:
        spec = planned.spec
        if spec.E > len(ITEMS) or spec.places > len(PLACES):
            raise ValueError(f"{spec.spec_id}: E={spec.E} and places={spec.places}, but gen/wordlists.py only has "
                             f"{len(ITEMS)} items and {len(PLACES)} places")


def build_dataset(config: dict) -> tuple[list[dict], dict]:
    """Run the whole pipeline in memory. Returns (records, stats)."""
    orders = plan(config)                                          # 1. settings -> orders
    _check_run_settings(config, orders)
    root_seed = config.get("root_seed", 0)
    max_attempts = config.get("max_attempts", DEFAULT_MAX_ATTEMPTS)
    records: list[dict] = []
    made: dict[str, int] = {}
    failed: dict[str, int] = {}
    not_buildable: dict[str, str] = {}
    validator_rejections = 0

    for planned in orders:
        spec = planned.spec
        made[spec.spec_id], failed[spec.spec_id] = 0, 0
        for story_number in range(planned.stories):                # 2. each story
            story_seed = seed_for(root_seed, spec.spec_id, story_number)
            last_reason = ""
            for attempt in range(max_attempts):
                attempt_seed = seed_for(story_seed, attempt)
                instance = generate(spec, attempt_seed)
                if isinstance(instance, Failure):
                    failed[spec.spec_id] += 1
                    last_reason = instance.reason
                    continue
                report = validate(instance, spec)
                if not report.ok:
                    failed[spec.spec_id] += 1
                    validator_rejections += 1
                    last_reason = "validator: " + "; ".join(report.problems)
                    log.warning("%s attempt %d rejected by validator: %s", spec.spec_id, attempt, last_reason)
                    continue
                trace = run(instance.universe, instance.setup, instance.body)
                rendered = render(instance, trace, stream(attempt_seed, "render"))
                records.append(_record(f"{spec.spec_id}/{story_number:03d}", spec, instance,
                                       trace, rendered, report.measured))
                made[spec.spec_id] += 1
                break
            else:
                not_buildable[spec.spec_id] = f"story {story_number}: {max_attempts} attempts failed; last: {last_reason}"
                log.warning("%s is NOT BUILDABLE (%s)", spec.spec_id, not_buildable[spec.spec_id])
                break                                              # stop wasting attempts on this order

    stats = {
        "stories_made_per_order": made,
        "failed_attempts_per_order": failed,
        "not_buildable": not_buildable,
        "validator_rejections": validator_rejections,
    }
    return records, stats


def _git_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent,
                             capture_output=True, text=True, timeout=10)
        return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "unknown"
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def build(config: dict, out_dir: str | Path) -> dict:
    """Write dataset.jsonl and manifest.json into out_dir. Returns the manifest."""
    records, stats = build_dataset(config)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    lines = [json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")) for r in records]
    data = ("\n".join(lines) + "\n").encode("utf-8") if lines else b""
    (out / "dataset.jsonl").write_bytes(data)

    manifest = {
        "git_commit": _git_commit(),
        "python_version": platform.python_version(),
        "root_seed": config.get("root_seed", 0),
        "max_attempts": config.get("max_attempts", DEFAULT_MAX_ATTEMPTS),
        "n_instances": len(records),
        **stats,
        "dataset_sha256": hashlib.sha256(data).hexdigest(),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main(argv: list[str] | None = None) -> int:
    import yaml  # only the command line needs PyYAML

    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2:
        print("usage: python -m dwsbench.build <config.yaml> <out_dir>", file=sys.stderr)
        return 2
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    config = yaml.safe_load(Path(argv[0]).read_text(encoding="utf-8"))
    manifest = build(config, argv[1])
    log.info("wrote %d stories to %s (sha256 %s)", manifest["n_instances"], argv[1], manifest["dataset_sha256"][:12])
    if manifest["not_buildable"]:
        log.warning("%d order(s) not buildable: %s", len(manifest["not_buildable"]), sorted(manifest["not_buildable"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
