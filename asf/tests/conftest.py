"""Shared fixtures: a hermetic home and a template clone built from this asf/.

Every test runs the scripts as a subprocess against real directories and real
git repositories under tmp_path, with HOME pointed at a private directory, so
nothing touches the real ~/.claude, ~/.gitconfig or ~/.zshrc. A fake `claude`
comes first on the PATH, so no test reaches the real CLI or the network.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ASF = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"
IGNORED = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache")


def system_env() -> dict[str, str]:
    """The variables a Windows process needs to start (SSL, cmd, PATHEXT); empty on Linux."""
    if not WINDOWS:
        return {}
    names = ("SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP")
    return {name: os.environ[name] for name in names if name in os.environ}


def symlink(link: Path, target: Path) -> None:
    """Create a symlink; skip the test where the machine allows none (Windows without the privilege)."""
    try:
        link.symlink_to(target)
    except OSError as error:
        pytest.skip(f"this machine cannot create symlinks: {error}")


@pytest.fixture
def home(tmp_path: Path) -> Path:
    path = tmp_path / "home"
    path.mkdir()
    return path


FAKE_CLAUDE = r'''#!/bin/sh
# A stand-in for the claude CLI: logs its arguments to $FAKE_CLAUDE_LOG and fails for
# the argument in $FAKE_CLAUDE_FAILS. `plugin marketplace add` rewrites the user
# settings the way the real CLI does, dropping each marketplace's autoUpdate.
echo "$*" >> "$FAKE_CLAUDE_LOG"
for last; do :; done
if [ -n "${FAKE_CLAUDE_FAILS:-}" ] && [ "$last" = "$FAKE_CLAUDE_FAILS" ]; then
    echo "Failed to install $last: not found in marketplace"
    exit 1
fi
settings="$HOME/.claude/settings.json"
if [ "$1 $2 $3" = "plugin marketplace add" ] && [ -f "$settings" ]; then
    "${PYTHON:-python3}" - "$settings" <<'EOF'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for spec in data.get("extraKnownMarketplaces", {}).values():
    spec.pop("autoUpdate", None)
open(sys.argv[1], "w", encoding="utf-8", newline=chr(10)).write(json.dumps(data, indent=2) + "\n")
EOF
fi
'''


@pytest.fixture
def env(home: Path, tmp_path: Path) -> dict[str, str]:
    tools = tmp_path / "bin"
    tools.mkdir()
    (tools / "claude").write_text(FAKE_CLAUDE, encoding="utf-8", newline="\n")
    (tools / "claude").chmod(0o755)
    if WINDOWS:
        # shutil.which finds a command through PATHEXT only, so the sh fake needs a .cmd wrapper
        (tools / "claude.cmd").write_text('@bash "%~dp0claude" %*\r\n', encoding="utf-8", newline="")
    return {
        **system_env(),
        "PYTHON": sys.executable.replace("\\", "/"),
        "PATH": f"{tools}{os.pathsep}{os.environ['PATH']}",
        "FAKE_CLAUDE_LOG": str(tmp_path / "claude.log"),
        "HOME": str(home),
        "USERPROFILE": str(home),
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
    # NTFS has no mode bit, so `git add` stages every file at 100644; a real clone keeps the committed modes
    real = git("ls-files", "-s", "asf", cwd=ASF.parent, env=env)
    for line in real.splitlines():
        meta, path = line.split("\t", 1)
        if meta.startswith("100755") and (root / path).is_file():
            git("update-index", "--chmod=+x", path, cwd=root, env=env)
    git("commit", "-q", "-m", "template", cwd=root, env=env)
    return root


def git(*args: str, cwd: Path, env: dict[str, str]) -> str:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), env=env, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout.strip()


def kasten(script_root: Path, *args: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    """Run asf/scripts/kasten.py of the Kasten or template at script_root."""
    return subprocess.run(
        [sys.executable, str(script_root / "asf" / "scripts" / "kasten.py"), *args],
        cwd=str(cwd), env=env, capture_output=True, text=True, encoding="utf-8",
    )
