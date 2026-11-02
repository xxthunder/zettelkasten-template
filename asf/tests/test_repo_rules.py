"""`asf/claude/hooks/repo-rules.py`: a session learns a neighbour repository's rules first.

Claude Code loads the CLAUDE.md and AGENTS.md of the directory a session starts in and of
its subdirectories, never those of a repository next to it. The hook runs before every
tool call; on the first call of a session that reaches into another repository it denies
the call and names that repository's rule files, its imports followed, to be read first.
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from conftest import ASF

HOOK = ASF / "claude" / "hooks" / "repo-rules.py"


@pytest.fixture
def dev(tmp_path: Path) -> Path:
    """~/dev with the Kasten the session starts in and a neighbour repository with rules."""
    root = tmp_path / "dev"
    for repo in ("kasten", "other"):
        (root / repo).mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(root / repo)], check=True)
    (root / "other" / "CLAUDE.md").write_text("@AGENTS.md\n")
    (root / "other" / "AGENTS.md").write_text("# Rules of other\n")
    return root


def run(dev: Path, tool: str, tool_input: dict, *, session: str = "s1", cwd: Path | None = None,
        raw: str | None = None) -> dict | None:
    payload = raw if raw is not None else json.dumps({
        "session_id": session, "cwd": str(cwd or dev / "kasten"), "hook_event_name": "PreToolUse",
        "tool_name": tool, "tool_input": tool_input,
    })
    result = subprocess.run(["python3", str(HOOK)], input=payload, capture_output=True, text=True,
                            env={"REPO_RULES_STATE": str(dev.parent / "state"), "HOME": str(dev.parent),
                                 "PATH": "/usr/bin:/bin"})
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


def denied(output: dict | None) -> str:
    assert output is not None, "the call was let through"
    hook = output["hookSpecificOutput"]
    assert hook["hookEventName"] == "PreToolUse"
    assert hook["permissionDecision"] == "deny"
    return hook["permissionDecisionReason"]


def test_the_first_call_into_a_neighbour_repository_is_denied_with_its_rule_files(dev):
    reason = denied(run(dev, "Read", {"file_path": str(dev / "other" / "README.md")}))
    assert str(dev / "other" / "CLAUDE.md") in reason
    assert str(dev / "other" / "AGENTS.md") in reason
    assert "read" in reason.lower()


def test_a_second_call_into_the_same_repository_goes_through(dev):
    run(dev, "Read", {"file_path": str(dev / "other" / "README.md")})
    assert run(dev, "Edit", {"file_path": str(dev / "other" / "src" / "x.py")}) is None


def test_another_session_is_denied_again(dev):
    run(dev, "Read", {"file_path": str(dev / "other" / "README.md")})
    denied(run(dev, "Read", {"file_path": str(dev / "other" / "README.md")}, session="s2"))


def test_the_sessions_own_repository_goes_through(dev):
    (dev / "kasten" / "AGENTS.md").write_text("# Kasten\n")
    assert run(dev, "Write", {"file_path": str(dev / "kasten" / "notes" / "new.md")}) is None


def test_a_repository_the_session_started_below_goes_through(dev):
    (dev / "kasten" / "sub").mkdir()
    (dev / "kasten" / "AGENTS.md").write_text("# Kasten\n")
    assert run(dev, "Read", {"file_path": str(dev / "kasten" / "AGENTS.md")},
               cwd=dev / "kasten" / "sub") is None


def test_a_worktree_of_the_sessions_own_repository_goes_through(dev):
    kasten = dev / "kasten"
    (kasten / "AGENTS.md").write_text("# Kasten\n")
    subprocess.run(["git", "-C", str(kasten), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-q", "--allow-empty", "-m", "start"], check=True)
    worktree = dev / "kasten.worktrees" / "item"
    subprocess.run(["git", "-C", str(kasten), "worktree", "add", "-q", str(worktree)], check=True)
    assert run(dev, "Edit", {"file_path": str(worktree / "AGENTS.md")}) is None


def test_a_worktree_of_a_neighbour_repository_names_the_worktrees_rule_files(dev):
    other = dev / "other"
    subprocess.run(["git", "-C", str(other), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(other), "-c", "user.name=t", "-c", "user.email=t@example.invalid",
                    "commit", "-q", "-m", "start"], check=True)
    worktree = dev / "other.worktrees" / "item"
    subprocess.run(["git", "-C", str(other), "worktree", "add", "-q", str(worktree)], check=True)
    reason = denied(run(dev, "Edit", {"file_path": str(worktree / "AGENTS.md")}))
    assert str(worktree / "AGENTS.md") in reason


def test_imports_are_followed_once_and_missing_or_quoted_ones_are_left_out(dev):
    other = dev / "other"
    (other / "docs").mkdir()
    (other / "AGENTS.md").write_text(
        "# Rules\n\nSee @docs/principles.md and @docs/missing.md, ask @someone.\n\n"
        "```\n@docs/example.md\n```\n"
    )
    (other / "docs" / "principles.md").write_text("Back to @../AGENTS.md\n")
    (other / "docs" / "example.md").write_text("an example\n")
    reason = denied(run(dev, "Read", {"file_path": str(other / "README.md")}))
    assert str(other / "docs" / "principles.md") in reason
    assert reason.count(str(other / "AGENTS.md")) == 1
    assert "missing.md" not in reason
    assert "example.md" not in reason


def test_a_rule_file_in_dot_claude_is_named_too(dev):
    (dev / "other" / ".claude").mkdir()
    (dev / "other" / ".claude" / "CLAUDE.md").write_text("# more rules\n")
    reason = denied(run(dev, "Read", {"file_path": str(dev / "other" / "README.md")}))
    assert str(dev / "other" / ".claude" / "CLAUDE.md") in reason


def test_a_file_that_does_not_exist_yet_counts_for_its_repository(dev):
    denied(run(dev, "Write", {"file_path": str(dev / "other" / "new" / "dir" / "file.md")}))


@pytest.mark.parametrize("tool, key", [("Glob", "path"), ("Grep", "path"), ("NotebookEdit", "notebook_path")])
def test_the_search_and_notebook_tools_count(dev, tool, key):
    denied(run(dev, tool, {key: str(dev / "other")}))


@pytest.mark.parametrize("command", [
    "git -C {other} status",
    "cd ../other && git log -1",
    "ls ~/dev/other",
    "grep -rn foo {other}/src | head",
])
def test_a_bash_command_that_names_a_path_in_the_repository_counts(dev, command):
    command = command.format(other=dev / "other")
    denied(run(dev, "Bash", {"command": command}))


def test_a_bash_command_that_names_two_repositories_names_both(dev):
    third = dev / "third"
    third.mkdir()
    subprocess.run(["git", "init", "-q", str(third)], check=True)
    (third / "AGENTS.md").write_text("# third\n")
    reason = denied(run(dev, "Bash", {"command": f"diff {dev / 'other' / 'AGENTS.md'} {third / 'AGENTS.md'}"}))
    assert str(dev / "other" / "AGENTS.md") in reason
    assert str(third / "AGENTS.md") in reason


def test_a_bash_command_without_such_a_path_goes_through(dev):
    assert run(dev, "Bash", {"command": "git status && echo 'a/b' > /dev/null"}) is None


def test_a_repository_without_rule_files_goes_through(dev):
    bare = dev / "bare"
    bare.mkdir()
    subprocess.run(["git", "init", "-q", str(bare)], check=True)
    assert run(dev, "Read", {"file_path": str(bare / "README.md")}) is None


def test_a_path_outside_any_repository_goes_through(dev, tmp_path):
    assert run(dev, "Read", {"file_path": str(tmp_path / "loose.txt")}) is None


@pytest.mark.parametrize("raw", ["", "not json", "{}", json.dumps({"tool_name": "Read", "tool_input": None})])
def test_input_it_cannot_read_lets_the_call_through(dev, raw):
    assert run(dev, "Read", {}, raw=raw) is None
