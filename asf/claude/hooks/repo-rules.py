#!/usr/bin/env python3
"""PreToolUse hook: a session reads a neighbour repository's rules before it works there.

Claude Code loads CLAUDE.md and AGENTS.md from the directory a session starts in, from
the directories above it and from its subdirectories — never from a repository next to
it, such as ~/dev/<org>/<repo> beside the Kasten. On the first tool call of a session
that reaches into such a repository, this hook denies the call and names the
repository's rule files — CLAUDE.md, .claude/CLAUDE.md and AGENTS.md, their @imports
followed — to be read in full before the call is tried again. Every later call into that
repository goes through.

A call reaches into a repository through the path a file tool names, or through an
absolute, home-relative or ./-relative path in a Bash command. A repository counts once
per session, its worktrees with it; the sessions' records live in $REPO_RULES_STATE, or
in claude-repo-rules/ under the system's temporary directory. Input it cannot read lets
the call through.

Standard library only, like every script in asf/.
"""
from __future__ import annotations

import json
import os
import re
import shlex
import sys
import tempfile
from pathlib import Path

PATH_KEYS = ("file_path", "notebook_path", "path")
RULE_FILES = ("CLAUDE.md", ".claude/CLAUDE.md", "AGENTS.md")
IMPORT = re.compile(r"(?:^|(?<=\s))@(\S+)")
MAX_IMPORT_DEPTH = 5


def repository(path: Path) -> Path | None:
    """The root of the git working tree that holds path, which need not exist yet."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def identity(root: Path) -> str:
    """The repository's common git directory, the same for all its worktrees."""
    dot_git = root / ".git"
    if dot_git.is_dir():
        return str(dot_git.resolve())
    match = re.match(r"gitdir:\s*(.+)", dot_git.read_text().strip())
    if not match:
        return str(dot_git.resolve())
    git_dir = (root / match.group(1)).resolve()
    common = git_dir / "commondir"
    if common.is_file():
        return str((git_dir / common.read_text().strip()).resolve())
    return str(git_dir)


def bash_paths(command: str, cwd: Path) -> list[Path]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
        lexer.whitespace_split = True
        tokens = list(lexer)
    except ValueError:
        tokens = command.split()
    paths = []
    for token in tokens:
        token = token.split("=", 1)[-1]
        if token.startswith(("/", "~", "./", "../")):
            paths.append(cwd / os.path.expanduser(token))
    return paths


def touched(tool_input: dict, cwd: Path) -> list[Path]:
    paths = [cwd / os.path.expanduser(value) for key in PATH_KEYS
             if isinstance(value := tool_input.get(key), str) and value]
    command = tool_input.get("command")
    if isinstance(command, str):
        paths += bash_paths(command, cwd)
    return [Path(os.path.normpath(path)) for path in paths]


def imports(text: str) -> list[str]:
    found, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if not fenced:
            found += IMPORT.findall(re.sub(r"`[^`]*`", "", line))
    return [name.rstrip(".,;:!?)") for name in found]


def rule_files(root: Path) -> list[Path]:
    """The repository's rule files in the order Claude Code reads them, imports inline."""
    seen: list[Path] = []

    def visit(path: Path, depth: int) -> None:
        path = path.resolve()
        if path in seen or not path.is_file():
            return
        seen.append(path)
        if depth < MAX_IMPORT_DEPTH:
            for name in imports(path.read_text(errors="replace")):
                visit(path.parent / os.path.expanduser(name), depth + 1)

    for name in RULE_FILES:
        visit(root / name, 0)
    return seen


def state_file(session: str) -> Path:
    directory = Path(os.environ.get("REPO_RULES_STATE") or Path(tempfile.gettempdir()) / "claude-repo-rules")
    directory.mkdir(parents=True, exist_ok=True)
    return directory / re.sub(r"[^A-Za-z0-9_.-]", "_", session)


def main() -> int:
    try:
        event = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(event, dict):
        return 0
    session, cwd, tool_input = event.get("session_id"), event.get("cwd"), event.get("tool_input")
    if not (isinstance(session, str) and isinstance(cwd, str) and isinstance(tool_input, dict)):
        return 0
    cwd_path = Path(cwd)
    own = repository(cwd_path)
    own_identity = identity(own) if own else None

    record = state_file(session)
    known = set(record.read_text().splitlines()) if record.is_file() else set()
    first: dict[str, Path] = {}
    for path in touched(tool_input, cwd_path):
        root = repository(path)
        if root is None or root.is_relative_to(cwd_path):
            continue
        key = identity(root)
        if key != own_identity and key not in known:
            first.setdefault(key, root)
    if not first:
        return 0
    with record.open("a") as log:
        log.writelines(f"{key}\n" for key in first)

    sections = []
    for root in first.values():
        files = rule_files(root)
        if files:
            sections.append(f"{root}:\n" + "".join(f"- {file}\n" for file in files))
    if not sections:
        return 0
    reason = ("This session reaches into another repository for the first time. Its rules govern "
              "everything done there — files, commits, backlog, the language of its artifacts. "
              "Read these files in full, then try the call again:\n\n" + "\n".join(sections))
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": reason,
    }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
