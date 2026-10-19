"""Test 7: plan, gen, validate and render never import each other (or build)."""
import ast
from pathlib import Path

PKG = Path(__file__).resolve().parent.parent / "dwsbench"
STAGES = {"plan", "gen", "validate", "render"}
UPPER = STAGES | {"build"}  # nothing below build.py may import these


def imported_modules(path: Path, root: Path = PKG.parent) -> list[str]:
    """Absolute dotted names imported by one file (relative imports are resolved).

    `root` is the folder that contains the `dwsbench` package.
    """
    rel = path.relative_to(root).with_suffix("")
    package_parts = list(rel.parts[:-1])  # the package a file lives in, for modules and __init__.py alike
    found = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            found += [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package_parts[: len(package_parts) - (node.level - 1)]
                base = ".".join(anchor + ([node.module] if node.module else []))
            found.append(base)
            found += [f"{base}.{a.name}" for a in node.names]  # catches `from dwsbench import gen`
    return found


def folder_of(dotted: str) -> str | None:
    parts = dotted.split(".")
    if parts[0] != "dwsbench" or len(parts) < 2:
        return None
    return parts[1]


def test_stages_do_not_import_each_other():
    for stage in STAGES:
        for path in (PKG / stage).glob("*.py"):
            for mod in imported_modules(path):
                other = folder_of(mod)
                assert not (other in UPPER and other != stage), f"{path.name} imports {mod}"


def test_core_and_ops_do_not_import_upwards():
    for folder in ("core", "ops"):
        for path in (PKG / folder).glob("*.py"):
            for mod in imported_modules(path):
                assert folder_of(mod) not in UPPER, f"{path.name} imports {mod}"


def test_checker_sees_a_planted_violation(tmp_path):
    # the planted file lives in a throw-away copy of the layout, never in the real source tree
    bad = tmp_path / "dwsbench" / "validate" / "_planted.py"
    bad.parent.mkdir(parents=True)
    bad.write_text("from dwsbench.gen.generator import generate\n")
    assert any(folder_of(m) == "gen" for m in imported_modules(bad, tmp_path))
