"""`asf/scripts/kasten.py`: make a new Kasten, set a machine up for it, update it.

`new` turns a template clone into a new Kasten with a history of its own;
`setup` points the user's Claude Code, git and zsh at a Kasten and can run any
number of times; `update` replaces a Kasten's asf/ with the template's and
commits the result.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import WINDOWS, git, kasten, symlink

REMOTE = "git@example.com:team/notes.git"


def make(template: Path, tmp_path: Path, env: dict[str, str], *args: str) -> Path:
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), *args, cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    return target


def commit(repo: Path, env: dict[str, str], message: str = "change") -> None:
    git("add", "-A", cwd=repo, env=env)
    git("commit", "-q", "-m", message, cwd=repo, env=env)


def set_executable(repo: Path, env: dict[str, str], relative: str) -> None:
    """Make a tracked file executable in the working tree and in the index (NTFS has no mode bit)."""
    (repo / relative).chmod(0o755)
    git("add", relative, cwd=repo, env=env)
    git("update-index", "--chmod=+x", relative, cwd=repo, env=env)


def index_mode(repo: Path, env: dict[str, str], relative: str) -> str:
    return git("ls-files", "-s", relative, cwd=repo, env=env).split()[0]


def settings(home: Path) -> dict:
    return json.loads((home / ".claude" / "settings.json").read_text(encoding="utf-8"))


# --- new ---------------------------------------------------------------------


def test_new_makes_a_kasten_from_asf_and_the_seed(template, tmp_path, env):
    target = make(template, tmp_path, env, "--remote", REMOTE)
    assert (target / "asf" / "AGENTS.md").is_file()
    assert "@asf/AGENTS.md" in (target / "AGENTS.md").read_text(encoding="utf-8")
    for seeded in ("CONVENTIONS.md", "README.md", "engineering/log.md", "engineering/board.md",
                   "engineering/repos.md", "learnings/README.md", "memory/MEMORY.md",
                   "docs/backlog/README.md", "docs/decisions/README.md", "claude/CLAUDE.md"):
        assert (target / seeded).is_file(), seeded
    assert not (target / "engineering" / "next.md").exists()
    assert (target / "asf" / "seed").is_dir()


def test_new_commits_on_develop_with_a_history_of_its_own(template, tmp_path, env):
    target = make(template, tmp_path, env, "--remote", REMOTE)
    assert git("branch", "--show-current", cwd=target, env=env) == "develop"
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "1"
    assert git("status", "--porcelain", cwd=target, env=env) == ""
    assert git("remote", "get-url", "origin", cwd=target, env=env) == REMOTE


def test_new_without_a_remote_has_no_origin(template, tmp_path, env):
    target = make(template, tmp_path, env)
    assert git("remote", cwd=target, env=env) == ""


def test_new_commits_no_memory_path(template, tmp_path, env):
    target = make(template, tmp_path, env)
    committed = target / ".claude" / "settings.json"
    if committed.exists():
        assert "autoMemoryDirectory" not in json.loads(committed.read_text(encoding="utf-8"))


def test_setup_points_auto_memory_at_its_own_memory_locally(template, tmp_path, env):
    target = make(template, tmp_path, env)
    local = json.loads((target / ".claude" / "settings.local.json").read_text(encoding="utf-8"))
    assert local["autoMemoryDirectory"] == str(target / "memory")
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_setup_keeps_other_local_settings(template, tmp_path, env):
    target = make(template, tmp_path, env)
    path = target / ".claude" / "settings.local.json"
    path.write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]}}), encoding="utf-8", newline="\n")
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    local = json.loads(path.read_text(encoding="utf-8"))
    assert local["permissions"] == {"allow": ["Bash(ls)"]}
    assert local["autoMemoryDirectory"] == str(target / "memory")


def test_the_seed_ignores_local_settings(template):
    lines = (template / "asf" / "seed" / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".claude/settings.local.json" in lines


def test_new_leaves_caches_behind(template, tmp_path, env):
    (template / "asf" / "scripts" / "__pycache__").mkdir()
    (template / "asf" / "scripts" / "__pycache__" / "kasten.pyc").write_text("x", encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env)
    assert not (target / "asf" / "scripts" / "__pycache__").exists()


def test_new_sets_the_machine_up(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    assert target.as_posix() in (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")


def test_new_records_the_template_commit_as_its_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    assert (target / ".asf-base").read_text(encoding="utf-8") == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"
    assert git("ls-files", ".asf-base", cwd=target, env=env) == ".asf-base"


def test_new_seeds_a_leak_patterns_file_that_holds_no_pattern(template, tmp_path, env):
    target = make(template, tmp_path, env)
    lines = (target / "scripts" / "leak-patterns.txt").read_text(encoding="utf-8").splitlines()
    assert lines and all(not line.strip() or line.startswith("#") for line in lines)


def test_new_seeds_an_executable_gate(template, tmp_path, env):
    target = make(template, tmp_path, env)
    gate = target / "scripts" / "gate"
    assert gate.is_file()
    if not WINDOWS:  # NTFS has no executable bit; the index mode below is what travels
        assert os.access(gate, os.X_OK)
    assert git("ls-files", "-s", "scripts/gate", cwd=target, env=env).startswith("100755")


def test_a_kasten_clone_keeps_lf_under_autocrlf(template, tmp_path, env):
    target = make(template, tmp_path, env)
    clone = tmp_path / "clone"
    git("-c", "core.autocrlf=true", "clone", "-q", str(target), str(clone), cwd=tmp_path, env=env)
    for script in ("asf/scripts/gate", "asf/scripts/lint.sh", "scripts/gate"):
        assert b"\r" not in (clone / script).read_bytes(), script


def test_new_takes_file_modes_from_the_template_index(template, tmp_path, env):
    seed = template / "asf" / "seed"
    (seed / "with-shebang.sh").write_text("#!/bin/sh\necho hi\n", encoding="utf-8", newline="\n")
    (seed / "no-shebang.txt").write_text("plain\n", encoding="utf-8", newline="\n")
    git("add", "-A", cwd=template, env=env)
    git("update-index", "--chmod=-x", "asf/seed/with-shebang.sh", cwd=template, env=env)
    git("update-index", "--chmod=+x", "asf/seed/no-shebang.txt", cwd=template, env=env)
    (seed / "no-shebang.txt").chmod(0o755)  # on Linux the working tree carries the mode too
    commit(template, env, "modes")
    target = make(template, tmp_path, env)
    assert index_mode(target, env, "with-shebang.sh") == "100644"
    assert index_mode(target, env, "no-shebang.txt") == "100755"


def test_new_refuses_a_target_that_is_not_empty(template, tmp_path, env):
    target = tmp_path / "notes"
    target.mkdir()
    (target / "keep.md").write_text("mine\n", encoding="utf-8", newline="\n")
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode != 0
    assert "not empty" in result.stderr
    assert (target / "keep.md").read_text(encoding="utf-8") == "mine\n"


# --- setup -------------------------------------------------------------------


def test_setup_writes_a_global_claude_md_that_imports_the_kasten(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    text = (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert f"@{target.as_posix()}/asf/claude/CLAUDE.md" in text
    assert f"@{target.as_posix()}/claude/CLAUDE.md" in text


def test_setup_keeps_a_copy_of_a_global_claude_md_it_did_not_write(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").write_text("# my old rules\n", encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env)
    kasten(target, "setup", cwd=target, env=env)
    backups = list((home / ".claude").glob("CLAUDE.md.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "# my old rules\n"


def test_setup_names_the_copy_of_a_global_claude_md_and_where_its_rules_go(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").write_text("# my old rules\n", encoding="utf-8", newline="\n")
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    [backup] = (home / ".claude").glob("CLAUDE.md.bak-*")
    assert str(backup) in result.stdout
    assert f"{target}/claude/CLAUDE.md" in result.stdout


def test_setup_merges_the_shared_settings_and_keeps_the_machines_own(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "model": "opus", "theme": "dark", "permissions": {"deny": ["Bash(rm -rf /)"]},
    }), encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env, "--remote", REMOTE)
    s = settings(home)
    assert s["model"] == "opus" and s["theme"] == "dark"
    assert s["permissions"]["deny"] == ["Bash(rm -rf /)"]
    assert s["enabledPlugins"]["xxthunder-dev-skills@xxthunder-agentic-skills"] is True
    assert "xxthunder-agentic-skills" in s["extraKnownMarketplaces"]
    assert s["hooks"] == {"PreToolUse": [repo_rules_hook(target)]}
    assert s["env"]["LOGBOOK_PATH"] == str(target)
    assert s["env"]["LEARNINGS_PATH"] == str(target)
    assert s["env"]["LOGBOOK_REMOTE"] == REMOTE
    assert s["env"]["LEARNINGS_REMOTE"] == REMOTE
    assert s["env"]["BOARD_PATH"] == str(target)
    assert s["env"]["BOARD_REMOTE"] == REMOTE


RULE_LISTS = (("permissions", "allow"), ("autoMode", "allow"), ("autoMode", "environment"))


def own_rules(shared: dict) -> dict:
    """User settings with one own entry before and one after the last shared entry of each list."""
    own: dict = {}
    for key, name in RULE_LISTS:
        own.setdefault(key, {})[name] = ["my own first", shared[key][name][-1], "my own last"]
    return own


def write_user_settings(home: Path, content: dict) -> None:
    (home / ".claude").mkdir(exist_ok=True)
    (home / ".claude" / "settings.json").write_text(json.dumps(content), encoding="utf-8", newline="\n")


def test_setup_gives_empty_settings_the_shared_rules(template, tmp_path, env, home):
    make(template, tmp_path, env)
    s, shared = settings(home), shared_settings(template)
    for key, name in RULE_LISTS:
        assert s[key][name] == shared[key][name], (key, name)


def test_setup_keeps_the_users_rules_in_place_and_adds_the_missing(template, tmp_path, env, home):
    shared = shared_settings(template)
    own = own_rules(shared)
    write_user_settings(home, own)
    make(template, tmp_path, env)
    s = settings(home)
    for key, name in RULE_LISTS:
        # own entries stay in place; the shared entries still missing follow in template order
        assert s[key][name] == own[key][name] + shared[key][name][:-1], (key, name)


def test_setup_twice_with_own_rules_changes_nothing(template, tmp_path, env, home):
    write_user_settings(home, own_rules(shared_settings(template)))
    target = make(template, tmp_path, env)
    shared = shared_settings(template)
    assert all(set(shared[key][name]) <= set(settings(home)[key][name]) for key, name in RULE_LISTS)
    before = (home / ".claude" / "settings.json").read_bytes()
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    assert (home / ".claude" / "settings.json").read_bytes() == before


def test_setup_sets_no_remote_variables_without_an_origin(template, tmp_path, env, home):
    make(template, tmp_path, env)
    assert "LOGBOOK_REMOTE" not in settings(home)["env"]
    assert "BOARD_REMOTE" not in settings(home)["env"]


PROXY = {
    "HTTPS_PROXY": "http://127.0.0.1:3128",
    "HTTP_PROXY": "http://127.0.0.1:3128",
    "NO_PROXY": "localhost,.example.com",
    "NODE_EXTRA_CA_CERTS": "/etc/ssl/certs/ca-certificates.crt",
}


def test_setup_copies_the_proxy_from_its_environment_over_older_values(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "env": {"HTTPS_PROXY": "http://old.example.com:8080"},
    }), encoding="utf-8", newline="\n")
    make(template, tmp_path, {**env, **PROXY})
    s = settings(home)
    assert {key: s["env"][key] for key in PROXY} == PROXY


def test_setup_removes_the_proxy_its_environment_no_longer_has(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "env": {**PROXY, "MY_OWN": "kept"},
    }), encoding="utf-8", newline="\n")
    make(template, tmp_path, env)
    s = settings(home)
    assert not set(PROXY) & set(s["env"])
    assert s["env"]["MY_OWN"] == "kept"


def test_setup_twice_with_a_proxy_changes_nothing(template, tmp_path, env, home):
    proxied = {**env, **PROXY}
    target = make(template, tmp_path, proxied)
    before = (home / ".claude" / "settings.json").read_bytes()
    result = kasten(target, "setup", cwd=target, env=proxied)
    assert result.returncode == 0, result.stderr
    assert (home / ".claude" / "settings.json").read_bytes() == before


def shared_settings(template: Path) -> dict:
    return json.loads((template / "asf" / "claude" / "settings.json").read_text(encoding="utf-8"))


def claude_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "claude.log"
    return log.read_text(encoding="utf-8").splitlines() if log.is_file() else []


def test_the_shared_settings_declare_the_marketplace_of_every_shared_plugin(template):
    shared = shared_settings(template)
    for plugin in shared["enabledPlugins"]:
        assert plugin.split("@")[1] in shared["extraKnownMarketplaces"], plugin


UNUSED_PLUGINS = ("example-skills@anthropic-agent-skills", "document-skills@anthropic-agent-skills",
                  "feature-dev@claude-plugins-official", "code-simplifier@claude-plugins-official",
                  "claude-md-management@claude-plugins-official", "context7@claude-plugins-official",
                  "code-review@claude-plugins-official")


def test_setup_turns_off_the_plugins_the_template_switches_off(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps(
        {"enabledPlugins": {plugin: True for plugin in UNUSED_PLUGINS}}), encoding="utf-8", newline="\n")
    make(template, tmp_path, env)
    assert all(settings(home)["enabledPlugins"][plugin] is False for plugin in UNUSED_PLUGINS)
    assert not any(f"plugin install {plugin}" in claude_calls(tmp_path) for plugin in UNUSED_PLUGINS)


def test_the_template_brings_no_ansible_lock(template):
    shared = shared_settings(template)
    assert "hooks" not in shared and "deny" not in shared.get("permissions", {})
    assert not (template / "asf" / "claude" / "hooks" / "deny-ansible.py").exists()


PLUGIN_SCRIPT = "/*/.claude/plugins/cache/*/scripts/*"


def test_the_template_allows_the_commands_of_the_closed_loop(template):
    shared = shared_settings(template)
    assert shared["permissions"]["allow"] == [
        "Bash(ssh *.devpod *)",
        f"Bash(uv run {PLUGIN_SCRIPT} *)",
        f"Bash({PLUGIN_SCRIPT} *)",
        "Bash(git push *)",
    ]


def test_the_template_explains_the_closed_loop_to_auto_mode(template):
    auto = shared_settings(template)["autoMode"]
    assert auto["allow"][0] == "$defaults" and auto["environment"][0] == "$defaults"
    allow = " ".join(auto["allow"])
    for phrase in ("ssh <workspace>.devpod", "~/.claude/plugins/cache/", "trusted checkout",
                   "asf/AGENTS.md", "default branch"):
        assert phrase in allow, phrase
    environment = " ".join(auto["environment"])
    for phrase in ("~/dev/<org>/<repo>", ".worktrees", "devpod"):
        assert phrase in environment, phrase


def test_setup_adds_the_shared_marketplaces(template, tmp_path, env):
    make(template, tmp_path, env)
    for spec in shared_settings(template)["extraKnownMarketplaces"].values():
        assert f"plugin marketplace add {spec['source']['repo']}" in claude_calls(tmp_path)


def test_setup_installs_every_shared_plugin_after_adding_the_marketplaces(template, tmp_path, env):
    make(template, tmp_path, env)
    calls = claude_calls(tmp_path)
    installs = [call for call in calls if call.startswith("plugin install ")]
    assert installs == [f"plugin install {plugin}"
                        for plugin, on in shared_settings(template)["enabledPlugins"].items() if on]
    assert calls.index(installs[0]) > max(i for i, call in enumerate(calls)
                                          if call.startswith("plugin marketplace add "))


def test_setup_keeps_the_shared_marketplace_settings_the_cli_rewrites(template, tmp_path, env, home):
    result = kasten(template, "new", str(tmp_path / "notes"), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "Could not run claude" not in result.stdout, result.stdout  # the fake itself must not fail
    assert settings(home)["extraKnownMarketplaces"]["xxthunder-agentic-skills"]["autoUpdate"] is True


def test_setup_names_a_plugin_it_could_not_install_and_finishes(template, tmp_path, env, home):
    env["FAKE_CLAUDE_FAILS"] = "xxthunder-dev-skills@xxthunder-agentic-skills"
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "xxthunder-dev-skills@xxthunder-agentic-skills" in result.stdout
    assert "not found in marketplace" in result.stdout
    assert "plugin install superpowers@claude-plugins-official" in claude_calls(tmp_path)
    if not WINDOWS:  # Windows writes no shell configuration (ZKK-023)
        assert (home / ".zshrc").is_file()


def test_setup_without_claude_on_the_path_says_so_and_finishes(template, tmp_path, env, home):
    tools = tmp_path / "no-claude"
    tools.mkdir()
    if WINDOWS:
        # Git for Windows and the Python shim need their neighbouring files, so link no copy:
        # the PATH holds their own directories, which hold no claude
        env["PATH"] = os.pathsep.join(dict.fromkeys(str(Path(tool).parent) for tool in (shutil.which("git"), sys.executable)))
    else:
        for name, real in (("git", shutil.which("git")), ("python3", sys.executable)):
            (tools / name).symlink_to(real)
        env["PATH"] = str(tools)
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "claude" in result.stdout and "setup again" in result.stdout
    if not WINDOWS:  # Windows writes no shell configuration (ZKK-023)
        assert (home / ".zshrc").is_file()


def test_setup_twice_changes_nothing(template, tmp_path, env, home):
    target = make(template, tmp_path, env, "--remote", REMOTE)
    files = [home / ".claude" / "settings.json", home / ".claude" / "CLAUDE.md", home / ".gitconfig"]
    if not WINDOWS:  # Windows writes no shell configuration (ZKK-023)
        files.append(home / ".zshrc")
    before = {p: p.read_bytes() for p in files}
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    assert {p: p.read_bytes() for p in before} == before
    assert list((home / ".claude").glob("*.bak-*")) == []


ANSIBLE_LOCK = {
    "matcher": "Bash",
    "hooks": [{"type": "command", "command": "\"$HOME/.claude/hooks/deny-ansible.py\"",
               "statusMessage": "Checking for Ansible"}],
}
OWN_HOOK = {"matcher": "Bash", "hooks": [{"type": "command", "command": "my-own-check"}]}


def repo_rules_hook(kasten: Path) -> dict:
    return {"matcher": "Read|Edit|Write|NotebookEdit|Glob|Grep|Bash",
            "hooks": [{"type": "command",
                       "command": f'python3 "{kasten.as_posix()}/asf/claude/hooks/repo-rules.py"'}]}


def test_setup_hooks_in_the_repo_rules_hook_of_the_kasten(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    assert settings(home)["hooks"]["PreToolUse"] == [repo_rules_hook(target)]
    assert (target / "asf" / "claude" / "hooks" / "repo-rules.py").is_file()


def test_setup_replaces_the_repo_rules_hook_of_another_kasten_and_keeps_the_rest(
        template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [repo_rules_hook(tmp_path / "old-kasten"), OWN_HOOK]},
    }), encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env)
    assert settings(home)["hooks"]["PreToolUse"] == [OWN_HOOK, repo_rules_hook(target)]


def test_setup_removes_the_ansible_lock_an_earlier_setup_made(template, tmp_path, env, home):
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    symlink(hooks / "deny-ansible.py", tmp_path / "old-kasten" / "deny-ansible.py")
    (hooks / "deny-ansible.py.bak-20261027161101").write_text("# my old hook\n", encoding="utf-8", newline="\n")
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"deny": ["Bash(ansible*)", "Bash(rm -rf /)", "Bash(molecule*)"]},
        "hooks": {"PreToolUse": [ANSIBLE_LOCK, OWN_HOOK]},
    }), encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env)
    s = settings(home)
    assert s["permissions"]["deny"] == ["Bash(rm -rf /)"]
    assert s["hooks"] == {"PreToolUse": [OWN_HOOK, repo_rules_hook(target)]}
    assert not (hooks / "deny-ansible.py").is_symlink()
    assert (hooks / "deny-ansible.py.bak-20261027161101").read_text(encoding="utf-8") == "# my old hook\n"


def test_setup_leaves_no_empty_settings_behind_the_ansible_lock(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"deny": ["Bash(ansible*)", "Bash(molecule*)"]},
        "hooks": {"PreToolUse": [ANSIBLE_LOCK]},
    }), encoding="utf-8", newline="\n")
    target = make(template, tmp_path, env)
    s = settings(home)
    assert "deny" not in s["permissions"]
    assert s["permissions"]["allow"] == shared_settings(template)["permissions"]["allow"]
    assert s["hooks"] == {"PreToolUse": [repo_rules_hook(target)]}


def test_setup_keeps_a_hook_file_of_that_name_it_did_not_link(template, tmp_path, env, home):
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "deny-ansible.py").write_text("# my own hook\n", encoding="utf-8", newline="\n")
    make(template, tmp_path, env)
    assert (hooks / "deny-ansible.py").read_text(encoding="utf-8") == "# my own hook\n"


def test_setup_sets_the_workflow_git_config(template, tmp_path, env):
    make(template, tmp_path, env)
    for key, value in (("pull.rebase", "true"), ("rebase.autoSquash", "true"),
                       ("push.autoSetupRemote", "true"), ("fetch.prune", "true"),
                       ("init.defaultBranch", "develop")):
        assert git("config", "--global", key, cwd=tmp_path, env=env) == value


@pytest.mark.skipif(WINDOWS, reason="the zsh fragment is hooked in on Linux and macOS only (ZKK-023)")
def test_setup_hooks_the_zsh_fragment_in_once(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    zshrc = (home / ".zshrc").read_text(encoding="utf-8")
    assert zshrc.count(f"source {target}/asf/shell/asf.zsh") == 1
    assert (target / "asf" / "shell" / "asf.zsh").is_file()


def test_setup_links_the_process_inbox_skill(template, tmp_path, env):
    target = make(template, tmp_path, env)
    link = target / ".claude" / "skills" / "process-inbox"
    if not WINDOWS:
        assert link.is_symlink()
    assert (link / "SKILL.md").is_file()
    assert git("status", "--porcelain", cwd=target, env=env) == ""


# --- update ------------------------------------------------------------------


def update(template: Path, target: Path, tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return kasten(template, "update", str(target), cwd=tmp_path, env=env)


def first_line_replaced(path: Path, line: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(line + "\n" + "".join(lines[1:]), encoding="utf-8", newline="\n")


def test_update_takes_the_templates_changes_and_commits(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "NEW.md").read_text(encoding="utf-8") == "new\n"
    assert not (target / "asf" / "README.md").exists()
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "2"
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_gives_an_older_kasten_an_executable_gate(template, tmp_path, env):
    target = make(template, tmp_path, env)
    git("rm", "-q", "scripts/gate", cwd=target, env=env)
    git("commit", "-q", "-m", "a Kasten from before the gate", cwd=target, env=env)
    (template / "asf" / "LATER.md").write_text("later\n", encoding="utf-8", newline="\n")
    commit(template, env, "a later template")
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert git("ls-files", "-s", "scripts/gate", cwd=target, env=env).startswith("100755")


def test_update_adds_new_seed_files_and_keeps_the_kastens_own(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "engineering" / "log.md").write_text("my log\n", encoding="utf-8", newline="\n")
    git("commit", "-q", "-am", "log", cwd=target, env=env)
    (template / "asf" / "seed" / "engineering" / "log.md").write_text("fresh\n", encoding="utf-8", newline="\n")
    (template / "asf" / "seed" / "glossary.md").write_text("glossary\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "engineering" / "log.md").read_text(encoding="utf-8") == "my log\n"
    assert (target / "glossary.md").read_text(encoding="utf-8") == "glossary\n"


def test_update_records_the_template_commit_as_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / ".asf-base").read_text(encoding="utf-8") == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"


def test_update_without_a_base_replaces_asf_and_records_one(template, tmp_path, env):
    target = make(template, tmp_path, env)
    git("rm", "-q", ".asf-base", cwd=target, env=env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    commit(target, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text(encoding="utf-8") == (template / "asf" / "AGENTS.md").read_text(encoding="utf-8")
    assert (target / ".asf-base").read_text(encoding="utf-8") == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"


def test_update_keeps_the_kastens_own_changes_to_asf(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    commit(target, env)
    (template / "asf" / "README.md").write_text("changed in the template\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text(encoding="utf-8") == "changed in the Kasten\n"
    assert (target / "asf" / "README.md").read_text(encoding="utf-8") == "changed in the template\n"


def test_update_merges_changes_to_different_lines_of_one_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    with (template / "asf" / "AGENTS.md").open("a", encoding="utf-8", newline="\n") as agents:
        agents.write("appended in the template\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    merged = (target / "asf" / "AGENTS.md").read_text(encoding="utf-8")
    assert merged.startswith("# changed in the Kasten\n")
    assert merged.endswith("appended in the template\n")
    assert "<<<<<<<" not in merged


def test_update_takes_new_and_deleted_files_and_keeps_the_kastens_new_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "MINE.md").write_text("mine\n", encoding="utf-8", newline="\n")
    commit(target, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "MINE.md").read_text(encoding="utf-8") == "mine\n"
    assert (target / "asf" / "NEW.md").read_text(encoding="utf-8") == "new\n"
    assert not (target / "asf" / "README.md").exists()


def test_update_keeps_the_mode_of_a_new_executable(template, tmp_path, env):
    target = make(template, tmp_path, env)
    script = template / "asf" / "scripts" / "new.sh"
    script.write_text("#!/bin/sh\n", encoding="utf-8", newline="\n")
    set_executable(template, env, "asf/scripts/new.sh")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert index_mode(target, env, "asf/scripts/new.sh") == "100755"
    if not WINDOWS:  # NTFS has no executable bit; the index mode above is what travels
        assert (target / "asf" / "scripts" / "new.sh").stat().st_mode & 0o111


def test_update_takes_a_mode_change_of_the_template(template, tmp_path, env):
    target = make(template, tmp_path, env)
    set_executable(template, env, "asf/README.md")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert index_mode(target, env, "asf/README.md") == "100755"
    if not WINDOWS:
        assert (target / "asf" / "README.md").stat().st_mode & 0o111


def test_update_takes_a_mode_change_on_a_merged_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    with (template / "asf" / "AGENTS.md").open("a", encoding="utf-8", newline="\n") as agents:
        agents.write("appended in the template\n")
    set_executable(template, env, "asf/AGENTS.md")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text(encoding="utf-8").startswith("# changed in the Kasten\n")
    assert index_mode(target, env, "asf/AGENTS.md") == "100755"
    if not WINDOWS:
        assert (target / "asf" / "AGENTS.md").stat().st_mode & 0o111


def test_update_takes_a_file_whose_name_is_not_ascii(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "Übersicht.md").write_text("new\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "Übersicht.md").read_text(encoding="utf-8") == "new\n"


def test_update_accepts_a_file_both_sides_deleted(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "README.md").unlink()
    commit(target, env)
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert not (target / "asf" / "README.md").exists()


def test_update_refuses_a_template_clone_behind_the_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    commit(template, env)
    assert update(template, target, tmp_path, env).returncode == 0
    git("reset", "-q", "--hard", "HEAD~1", cwd=template, env=env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "behind" in result.stderr
    assert (target / "asf" / "NEW.md").read_text(encoding="utf-8") == "new\n"
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_leaves_markers_on_a_conflict_and_does_not_commit(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    first_line_replaced(template / "asf" / "AGENTS.md", "# changed in the template")
    commit(template, env)
    calls = (tmp_path / "claude.log").read_text(encoding="utf-8")
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "asf/AGENTS.md" in result.stderr
    assert "<<<<<<< kasten" in (target / "asf" / "AGENTS.md").read_text(encoding="utf-8")
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "2"
    assert (tmp_path / "claude.log").read_text(encoding="utf-8") == calls


def test_update_reports_a_file_one_side_deleted_and_the_other_changed(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "README.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    commit(target, env)
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "asf/README.md" in result.stderr
    assert (target / "asf" / "README.md").read_text(encoding="utf-8") == "changed in the Kasten\n"


def test_update_refuses_a_template_clone_with_uncommitted_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "uncommitted" in result.stderr
    assert not (target / "asf" / "NEW.md").exists()
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_refuses_a_base_the_template_clone_does_not_have(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / ".asf-base").write_text("0" * 40 + "\n", encoding="utf-8", newline="\n")
    commit(target, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "git pull" in result.stderr
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_after_an_export_only_moves_the_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    commit(target, env)
    assert export(target, template, tmp_path, env, LEAK).returncode == 0
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert git("show", "--name-only", "--format=", "HEAD", cwd=target, env=env) == ".asf-base"
    second = export(target, template, tmp_path, env, LEAK)
    assert second.returncode == 0, second.stderr


def test_update_without_changes_makes_no_commit(template, tmp_path, env):
    target = make(template, tmp_path, env)
    result = kasten(template, "update", str(target), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "1"


def test_update_refuses_a_kasten_with_uncommitted_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "AGENTS.md").write_text("changed\n", encoding="utf-8", newline="\n")
    result = kasten(template, "update", str(target), cwd=tmp_path, env=env)
    assert result.returncode != 0
    assert "uncommitted" in result.stderr


def test_update_refuses_a_directory_that_is_no_kasten(template, tmp_path, env):
    other = tmp_path / "other"
    other.mkdir()
    git("init", "-q", cwd=other, env=env)
    result = kasten(template, "update", str(other), cwd=tmp_path, env=env)
    assert result.returncode != 0
    assert "no Kasten" in result.stderr


def test_setup_replaces_a_linked_global_claude_md_without_writing_through_it(template, tmp_path, env, home):
    elsewhere = tmp_path / "dotfiles-claude.md"
    elsewhere.write_text("# kept\n", encoding="utf-8", newline="\n")
    (home / ".claude").mkdir()
    symlink(home / ".claude" / "CLAUDE.md", elsewhere)
    make(template, tmp_path, env)
    assert elsewhere.read_text(encoding="utf-8") == "# kept\n"
    assert not (home / ".claude" / "CLAUDE.md").is_symlink()


# --- export ------------------------------------------------------------------


# The private name the tests leak, assembled so that it never stands whole in this
# file: the export checks asf/, and these tests are part of it.
LEAK = "secret" "-host"


def patterns(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "leak-patterns.txt"
    path.write_text("\n".join(("# private names", "", *lines)) + "\n", encoding="utf-8", newline="\n")
    return path


def export(source: Path, dest: Path, tmp_path: Path, env: dict[str, str],
           *lines: str) -> subprocess.CompletedProcess:
    """Export the asf/ of the Kasten at source into the template clone at dest."""
    return kasten(source, "export", str(dest), "--patterns", str(patterns(tmp_path, *lines)),
                  cwd=tmp_path, env=env)


def test_export_writes_asf_and_the_template_root(template, tmp_path, env):
    target = make(template, tmp_path, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert (template / "asf" / "AGENTS.md").is_file()
    for name in ("README.md", "AGENTS.md", "CLAUDE.md", "LICENSE"):
        assert (template / name).is_file(), name


def test_export_copies_folders_of_the_template_root(template, tmp_path, env):
    target = make(template, tmp_path, env)
    workflow = target / "asf" / "template" / ".github" / "workflows" / "gate.yml"
    workflow.parent.mkdir(parents=True, exist_ok=True)
    workflow.write_text("name: gate\n", encoding="utf-8", newline="\n")
    commit(target, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    copied = template / ".github" / "workflows" / "gate.yml"
    assert copied.read_text(encoding="utf-8") == "name: gate\n"


def test_export_gives_exactly_the_kastens_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    commit(target, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert git("status", "--porcelain", "--", "asf", cwd=template, env=env) == "M asf/AGENTS.md"


def test_export_replaces_what_was_there_but_keeps_git(template, tmp_path, env):
    (template / "stale.md").write_text("old\n", encoding="utf-8", newline="\n")
    commit(template, env)
    target = make(template, tmp_path, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert not (template / "stale.md").exists()
    assert (template / ".git").is_dir()


def test_export_leaves_caches_behind(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "scripts" / "__pycache__").mkdir()
    (target / "asf" / "scripts" / "__pycache__" / "kasten.pyc").write_text("x", encoding="utf-8", newline="\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert not (template / "asf" / "scripts" / "__pycache__").exists()


def test_export_stops_at_a_leak_and_writes_nothing(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "CONVENTIONS.md").write_text(f"ok\nssh to {LEAK.title()}.lan\n", encoding="utf-8", newline="\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "asf/CONVENTIONS.md:2" in result.stderr
    assert LEAK in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == ""


def test_export_checks_the_template_root_files_too(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "template" / "README.md").write_text(f"by {LEAK}\n", encoding="utf-8", newline="\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "asf/template/README.md:1" in result.stderr


def test_export_needs_a_patterns_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    result = kasten(target, "export", str(template), "--patterns", str(tmp_path / "missing.txt"),
                    cwd=tmp_path, env=env)
    assert result.returncode != 0
    assert "missing.txt" in result.stderr


def test_export_refuses_a_patterns_file_that_holds_no_pattern(template, tmp_path, env):
    target = make(template, tmp_path, env)
    result = export(target, template, tmp_path, env)
    assert result.returncode != 0
    assert "no pattern" in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == ""


def test_export_refuses_a_kasten_without_a_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    git("rm", "-q", ".asf-base", cwd=target, env=env)
    commit(target, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "update" in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == ""


def test_export_refuses_a_template_clone_with_uncommitted_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n", encoding="utf-8", newline="\n")
    (template / "asf" / "NOTE.md").write_text("draft\n", encoding="utf-8", newline="\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "uncommitted" in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == "?? asf/NOTE.md"


def test_export_refuses_when_the_template_moved_past_the_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("from the other Kasten\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "update" in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == ""
    assert (template / "asf" / "NEW.md").is_file()


def test_export_refuses_a_clone_behind_its_upstream(template, tmp_path, env):
    public = tmp_path / "public"
    git("clone", "-q", str(template), str(public), cwd=tmp_path, env=env)
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("from the other Kasten\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = export(target, public, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "behind" in result.stderr
    assert git("status", "--porcelain", cwd=public, env=env) == ""


def test_export_refuses_a_destination_that_is_no_git_repository(template, tmp_path, env):
    target = make(template, tmp_path, env)
    plain = tmp_path / "plain"
    plain.mkdir()
    result = export(target, plain, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "no git repository" in result.stderr
    assert list(plain.iterdir()) == []


# --- Windows (ZKK-023) --------------------------------------------------------


def test_setup_makes_the_process_inbox_skill_available(template, tmp_path, env):
    target = make(template, tmp_path, env)
    assert (target / ".claude" / "skills" / "process-inbox" / "SKILL.md").is_file()


def test_setup_twice_leaves_no_backup_of_the_skill(template, tmp_path, env):
    target = make(template, tmp_path, env)
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    skills = target / ".claude" / "skills"
    assert [entry.name for entry in skills.iterdir() if ".bak-" in entry.name] == []
    assert (skills / "process-inbox" / "SKILL.md").is_file()


def test_setup_keeps_non_ascii_user_settings(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_bytes(
        json.dumps({"x": "Gedankenstrich — Ümlaut"}, ensure_ascii=False).encode("utf-8"))
    result = kasten(template, "new", str(tmp_path / "notes"), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "Could not run claude" not in result.stdout, result.stdout  # the fake itself must not fail
    assert settings(home)["x"] == "Gedankenstrich — Ümlaut"


def test_setup_writes_lf_line_ends(template, tmp_path, env, home):
    make(template, tmp_path, env)
    for name in ("CLAUDE.md", "settings.json"):
        assert b"\r\n" not in (home / ".claude" / name).read_bytes(), name


@pytest.mark.skipif(not WINDOWS, reason="on Linux and macOS setup hooks in ~/.zshrc on purpose")
def test_setup_writes_no_shell_configuration_on_windows(template, tmp_path, env, home):
    make(template, tmp_path, env)
    assert not (home / ".zshrc").exists()


def hook_command(home: Path) -> str:
    return settings(home)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]


def test_the_hook_command_names_a_python_on_the_path(template, tmp_path, env, home):
    make(template, tmp_path, env)
    interpreter = hook_command(home).split()[0]
    assert shutil.which(interpreter, path=env["PATH"]), interpreter


@pytest.mark.skipif(not WINDOWS, reason="builds a PATH with python but no python3; the Windows case")
def test_the_hook_command_names_python_where_python3_is_missing(template, tmp_path, env, home):
    tools = tmp_path / "bin-python-only"
    tools.mkdir()
    (tools / "python.cmd").write_text(f'@"{sys.executable}" %*\r\n', encoding="utf-8", newline="")
    fake_claude = Path(env["PATH"].split(os.pathsep)[0])
    shutil.copy(fake_claude / "claude", tools / "claude")
    shutil.copy(fake_claude / "claude.cmd", tools / "claude.cmd")
    dirs = [str(tools)] + [str(Path(shutil.which(name)).parent) for name in ("git", "bash")]
    only = {**env, "PATH": os.pathsep.join(dict.fromkeys(dirs))}
    if shutil.which("python3", path=only["PATH"]):
        pytest.skip("python3 is in the git or bash directory of this machine")
    assert shutil.which("python", path=only["PATH"])
    target = tmp_path / "notes"
    result = subprocess.run(
        [sys.executable, str(template / "asf" / "scripts" / "kasten.py"), "new", str(target)],
        cwd=str(tmp_path), env=only, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    interpreter = hook_command(home).split()[0]
    assert interpreter == "python"
    assert shutil.which(interpreter, path=only["PATH"])


@pytest.mark.skipif(not WINDOWS, reason="Windows 11 App Execution Alias stubs exist only on Windows")
def test_the_hook_command_skips_a_store_stub_on_windows(template, tmp_path, env, home):
    stub_dir = tmp_path / "WindowsApps"
    stub_dir.mkdir()
    (stub_dir / "python3.cmd").write_text("@exit /b 9\r\n", encoding="utf-8", newline="")
    real_dir = tmp_path / "bin-real-python"
    real_dir.mkdir()
    (real_dir / "python.cmd").write_text(f'@"{sys.executable}" %*\r\n', encoding="utf-8", newline="")
    fake_claude = Path(env["PATH"].split(os.pathsep)[0])
    shutil.copy(fake_claude / "claude", real_dir / "claude")
    shutil.copy(fake_claude / "claude.cmd", real_dir / "claude.cmd")
    dirs = [str(stub_dir), str(real_dir)] + [str(Path(shutil.which(name)).parent) for name in ("git", "bash")]
    only = {**env, "PATH": os.pathsep.join(dict.fromkeys(dirs))}
    found = shutil.which("python3", path=only["PATH"])
    if not found or Path(found).parent != stub_dir:
        pytest.skip("another python3 comes before the stub on this machine")
    target = tmp_path / "notes"
    result = subprocess.run(
        [sys.executable, str(template / "asf" / "scripts" / "kasten.py"), "new", str(target)],
        cwd=str(tmp_path), env=only, capture_output=True, text=True, encoding="utf-8")
    assert result.returncode == 0, result.stderr
    assert hook_command(home).startswith("python "), hook_command(home)


# --- final review fixes (ZKK-023) ----------------------------------------------

LOCAL_SETTINGS = ".claude/settings.local.json"


def test_setup_adds_the_local_settings_to_gitignore_once(template, tmp_path, env):
    target = make(template, tmp_path, env)
    for _ in range(2):
        result = kasten(target, "setup", cwd=target, env=env)
        assert result.returncode == 0, result.stderr
    lines = (target / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert lines.count(LOCAL_SETTINGS) == 1


def test_update_does_not_commit_the_local_settings_of_an_older_kasten(template, tmp_path, env):
    target = make(template, tmp_path, env)
    ignore = target / ".gitignore"
    lines = ignore.read_text(encoding="utf-8").splitlines()
    kept = []
    for line in lines:
        if line == LOCAL_SETTINGS:
            if kept and kept[-1].startswith("#"):
                kept.pop()
            continue
        kept.append(line)
    ignore.write_text("\n".join(kept) + "\n", encoding="utf-8", newline="\n")
    (target / LOCAL_SETTINGS).unlink()
    commit(target, env, "older kasten")
    assert LOCAL_SETTINGS not in git("ls-files", cwd=target, env=env).splitlines()
    (template / "asf" / "NEW.md").write_text("new\n", encoding="utf-8", newline="\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    tracked = git("ls-files", cwd=target, env=env).splitlines()
    assert LOCAL_SETTINGS not in tracked
    assert LOCAL_SETTINGS in ignore.read_text(encoding="utf-8").splitlines()


def test_generated_paths_use_forward_slashes(template, tmp_path, env, home):
    make(template, tmp_path, env)
    assert "\\" not in (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8")
    assert "\\" not in hook_command(home)


@pytest.mark.skipif(WINDOWS, reason="a symlink needs a privilege on Windows")
def test_setup_keeps_a_correct_skill_link(template, tmp_path, env):
    target = make(template, tmp_path, env)
    link = target / ".claude" / "skills" / "process-inbox"
    before = os.lstat(link)
    destination = os.readlink(link)
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    after = os.lstat(link)
    assert (after.st_ino, after.st_mtime_ns) == (before.st_ino, before.st_mtime_ns)
    assert os.readlink(link) == destination
    assert [e.name for e in link.parent.iterdir() if ".bak-" in e.name] == []


@pytest.mark.skipif(WINDOWS, reason="a symlink needs a privilege on Windows")
def test_setup_replaces_a_wrong_skill_link(template, tmp_path, env):
    target = make(template, tmp_path, env)
    link = target / ".claude" / "skills" / "process-inbox"
    link.unlink()
    link.symlink_to("../../asf", target_is_directory=True)
    result = kasten(target, "setup", cwd=target, env=env)
    assert result.returncode == 0, result.stderr
    assert os.readlink(link) == "../../asf/skills/process-inbox"
    assert (link / "SKILL.md").is_file()
