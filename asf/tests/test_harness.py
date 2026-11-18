"""Checks on the test suite itself."""
import ast
from pathlib import Path

TESTS = Path(__file__).parent


def test_no_test_starts_a_bare_bash():
    # On Windows, a bare "bash" can resolve to System32\bash.exe, the WSL launcher,
    # instead of Git Bash. Tests must start the bash that shutil.which finds.
    found = []
    for path in sorted(TESTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.Call) and node.args):
                continue
            first = node.args[0]
            if (
                isinstance(first, ast.List)
                and first.elts
                and isinstance(first.elts[0], ast.Constant)
                and first.elts[0].value == "bash"
            ):
                found.append(f"{path.relative_to(TESTS).as_posix()}:{node.lineno}")
    assert found == [], f"tests start a bare bash: {found}"
