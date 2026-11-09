"""`scripts/gate`: one call that runs the template's tests and the lint.

The gate exits 0 only when both are green, and runs the lint also after red
tests, so one run shows every failure. Each test builds a small Kasten: the gate,
the lint, the test harness's pyproject and a single test that passes or fails.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from conftest import ASF

PASSING = "def test_passes():\n    assert True\n"
FAILING = "def test_fails():\n    assert False\n"


def make_kasten(root: Path, test: str = PASSING) -> Path:
    scripts = root / "asf" / "scripts"
    scripts.mkdir(parents=True)
    for script in ("gate", "lint.sh"):
        shutil.copy2(ASF / "scripts" / script, scripts / script)
    for harness in ("pyproject.toml", "uv.lock"):
        shutil.copy2(ASF / harness, root / "asf" / harness)
    (root / "asf" / "tests").mkdir()
    (root / "asf" / "tests" / "test_one.py").write_text(test)
    (root / "scripts").mkdir()
    shutil.copy2(ASF / "seed" / "scripts" / "gate", root / "scripts" / "gate")
    return root


def gate(kasten: Path, cwd: Path) -> subprocess.CompletedProcess:
    # Without the outer uv run's venv, the inner one prints no mismatch warning.
    env = {k: v for k, v in os.environ.items() if k != "VIRTUAL_ENV"}
    return subprocess.run([str(kasten / "scripts" / "gate")], cwd=str(cwd), env=env,
                          capture_output=True, text=True)


def test_green_tests_and_clean_lint_pass(tmp_path):
    kasten = make_kasten(tmp_path / "k")
    result = gate(kasten, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "1 passed" in result.stdout
    assert "Done: 0 errors" in result.stdout


def test_red_tests_fail_and_the_lint_still_runs(tmp_path):
    kasten = make_kasten(tmp_path / "k", FAILING)
    result = gate(kasten, tmp_path)
    assert result.returncode != 0
    assert "1 failed" in result.stdout
    assert "Done: 0 errors" in result.stdout


def test_red_lint_fails(tmp_path):
    kasten = make_kasten(tmp_path / "k")
    (kasten / "garden").mkdir()
    (kasten / "garden" / "README.md").write_text("# no frontmatter\n")
    result = gate(kasten, tmp_path)
    assert result.returncode != 0
    assert "Missing frontmatter: garden/README.md" in result.stdout
