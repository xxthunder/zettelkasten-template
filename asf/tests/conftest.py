"""Shared fixtures: a hermetic home and a template clone built from this asf/.

Every test runs the scripts as a subprocess against real directories and real
git repositories under tmp_path, with HOME pointed at a private directory, so
nothing touches the real ~/.claude, ~/.gitconfig or ~/.zshrc.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ASF = Path(__file__).resolve().parents[1]
IGNORED = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    return path


@pytest.fixture
def env(home: Path, tmp_path: Path) -> dict[str, str]:
    return {
        "PATH": os.environ["PATH"],
        "HOME": str(home),
        "XDG_CONFIG_HOME": str(home / ".config"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.invalid",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.invalid",
    }


@pytest.fixture
def template(tmp_path: Path, env: dict[str, str]) -> Path:
    """A clone of the template: this asf/ in a git repository of its own."""
    root = tmp_path / "template"
    shutil.copytree(ASF, root / "asf", ignore=IGNORED)
    git("init", "-q", "-b", "main", cwd=root, env=env)
    git("add", "-A", cwd=root, env=env)
    git("commit", "-q", "-m", "template", cwd=root, env=env)
    return root


def git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), env=env, check=True, capture_output=True, text=True
    ).stdout.strip()


def kasten(script_root: Path, *args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run asf/scripts/kasten.py of the Kasten or template at script_root."""
    return subprocess.run(
        ["python3", str(script_root / "asf" / "scripts" / "kasten.py"), *args],
        cwd=str(cwd), env=env, capture_output=True, text=True,
    )
