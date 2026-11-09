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
from pathlib import Path

from conftest import git, kasten

REMOTE = "git@example.com:team/notes.git"


def make(template: Path, tmp_path: Path, env: dict[str, str], *args: str) -> Path:
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), *args, cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    return target


def commit(repo: Path, env: dict[str, str], message: str = "change") -> None:
    git("add", "-A", cwd=repo, env=env)
    git("commit", "-q", "-m", message, cwd=repo, env=env)


def settings(home: Path) -> dict:
    return json.loads((home / ".claude" / "settings.json").read_text())


# --- new ---------------------------------------------------------------------


def test_new_makes_a_kasten_from_asf_and_the_seed(template, tmp_path, env):
    target = make(template, tmp_path, env, "--remote", REMOTE)
    assert (target / "asf" / "AGENTS.md").is_file()
    assert "@asf/AGENTS.md" in (target / "AGENTS.md").read_text()
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


def test_new_points_auto_memory_at_its_own_memory(template, tmp_path, env):
    target = make(template, tmp_path, env)
    project = json.loads((target / ".claude" / "settings.json").read_text())
    assert project["autoMemoryDirectory"] == str(target / "memory")


def test_new_leaves_caches_behind(template, tmp_path, env):
    (template / "asf" / "scripts" / "__pycache__").mkdir()
    (template / "asf" / "scripts" / "__pycache__" / "kasten.pyc").write_text("x")
    target = make(template, tmp_path, env)
    assert not (target / "asf" / "scripts" / "__pycache__").exists()


def test_new_sets_the_machine_up(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    assert str(target) in (home / ".claude" / "CLAUDE.md").read_text()


def test_new_records_the_template_commit_as_its_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    assert (target / ".asf-base").read_text() == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"
    assert git("ls-files", ".asf-base", cwd=target, env=env) == ".asf-base"


def test_new_seeds_a_leak_patterns_file_that_holds_no_pattern(template, tmp_path, env):
    target = make(template, tmp_path, env)
    lines = (target / "scripts" / "leak-patterns.txt").read_text().splitlines()
    assert lines and all(not line.strip() or line.startswith("#") for line in lines)


def test_new_seeds_an_executable_gate(template, tmp_path, env):
    target = make(template, tmp_path, env)
    gate = target / "scripts" / "gate"
    assert gate.is_file() and os.access(gate, os.X_OK)
    assert git("ls-files", "-s", "scripts/gate", cwd=target, env=env).startswith("100755")


def test_new_refuses_a_target_that_is_not_empty(template, tmp_path, env):
    target = tmp_path / "notes"
    target.mkdir()
    (target / "keep.md").write_text("mine\n")
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode != 0
    assert "not empty" in result.stderr
    assert (target / "keep.md").read_text() == "mine\n"


# --- setup -------------------------------------------------------------------


def test_setup_writes_a_global_claude_md_that_imports_the_kasten(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    text = (home / ".claude" / "CLAUDE.md").read_text()
    assert f"@{target}/asf/claude/CLAUDE.md" in text
    assert f"@{target}/claude/CLAUDE.md" in text


def test_setup_keeps_a_copy_of_a_global_claude_md_it_did_not_write(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").write_text("# my old rules\n")
    target = make(template, tmp_path, env)
    kasten(target, "setup", cwd=target, env=env)
    backups = list((home / ".claude").glob("CLAUDE.md.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "# my old rules\n"


def test_setup_names_the_copy_of_a_global_claude_md_and_where_its_rules_go(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").write_text("# my old rules\n")
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    [backup] = (home / ".claude").glob("CLAUDE.md.bak-*")
    assert str(backup) in result.stdout
    assert f"{target}/claude/CLAUDE.md" in result.stdout


def test_setup_merges_the_shared_settings_and_keeps_the_machines_own(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "model": "opus", "theme": "dark", "permissions": {"deny": ["Bash(rm -rf /)"]},
    }))
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
    }))
    make(template, tmp_path, {**env, **PROXY})
    s = settings(home)
    assert {key: s["env"][key] for key in PROXY} == PROXY


def test_setup_removes_the_proxy_its_environment_no_longer_has(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "env": {**PROXY, "MY_OWN": "kept"},
    }))
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
    return json.loads((template / "asf" / "claude" / "settings.json").read_text())


def claude_calls(tmp_path: Path) -> list[str]:
    log = tmp_path / "claude.log"
    return log.read_text().splitlines() if log.is_file() else []


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
        {"enabledPlugins": {plugin: True for plugin in UNUSED_PLUGINS}}))
    make(template, tmp_path, env)
    assert all(settings(home)["enabledPlugins"][plugin] is False for plugin in UNUSED_PLUGINS)
    assert not any(f"plugin install {plugin}" in claude_calls(tmp_path) for plugin in UNUSED_PLUGINS)


def test_the_template_brings_no_ansible_lock(template):
    shared = shared_settings(template)
    assert "hooks" not in shared and "permissions" not in shared
    assert not (template / "asf" / "claude" / "hooks" / "deny-ansible.py").exists()


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
    make(template, tmp_path, env)
    assert settings(home)["extraKnownMarketplaces"]["xxthunder-agentic-skills"]["autoUpdate"] is True


def test_setup_names_a_plugin_it_could_not_install_and_finishes(template, tmp_path, env, home):
    env["FAKE_CLAUDE_FAILS"] = "xxthunder-dev-skills@xxthunder-agentic-skills"
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "xxthunder-dev-skills@xxthunder-agentic-skills" in result.stdout
    assert "not found in marketplace" in result.stdout
    assert "plugin install superpowers@claude-plugins-official" in claude_calls(tmp_path)
    assert (home / ".zshrc").is_file()


def test_setup_without_claude_on_the_path_says_so_and_finishes(template, tmp_path, env, home):
    tools = tmp_path / "no-claude"
    tools.mkdir()
    for tool in ("git", "python3"):
        (tools / tool).symlink_to(shutil.which(tool))
    env["PATH"] = str(tools)
    target = tmp_path / "notes"
    result = kasten(template, "new", str(target), cwd=tmp_path, env=env)
    assert result.returncode == 0, result.stderr
    assert "claude" in result.stdout and "setup again" in result.stdout
    assert (home / ".zshrc").is_file()


def test_setup_twice_changes_nothing(template, tmp_path, env, home):
    target = make(template, tmp_path, env, "--remote", REMOTE)
    before = {p: p.read_bytes() for p in (home / ".claude" / "settings.json",
                                          home / ".claude" / "CLAUDE.md",
                                          home / ".zshrc", home / ".gitconfig")}
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
                       "command": f'python3 "{kasten}/asf/claude/hooks/repo-rules.py"'}]}


def test_setup_hooks_in_the_repo_rules_hook_of_the_kasten(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    assert settings(home)["hooks"]["PreToolUse"] == [repo_rules_hook(target)]
    assert (target / "asf" / "claude" / "hooks" / "repo-rules.py").is_file()


def test_setup_replaces_the_repo_rules_hook_of_another_kasten_and_keeps_the_rest(
        template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "hooks": {"PreToolUse": [repo_rules_hook(tmp_path / "old-kasten"), OWN_HOOK]},
    }))
    target = make(template, tmp_path, env)
    assert settings(home)["hooks"]["PreToolUse"] == [OWN_HOOK, repo_rules_hook(target)]


def test_setup_removes_the_ansible_lock_an_earlier_setup_made(template, tmp_path, env, home):
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "deny-ansible.py").symlink_to(tmp_path / "old-kasten" / "deny-ansible.py")
    (hooks / "deny-ansible.py.bak-20261027161101").write_text("# my old hook\n")
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"deny": ["Bash(ansible*)", "Bash(rm -rf /)", "Bash(molecule*)"]},
        "hooks": {"PreToolUse": [ANSIBLE_LOCK, OWN_HOOK]},
    }))
    target = make(template, tmp_path, env)
    s = settings(home)
    assert s["permissions"]["deny"] == ["Bash(rm -rf /)"]
    assert s["hooks"] == {"PreToolUse": [OWN_HOOK, repo_rules_hook(target)]}
    assert not (hooks / "deny-ansible.py").is_symlink()
    assert (hooks / "deny-ansible.py.bak-20261027161101").read_text() == "# my old hook\n"


def test_setup_leaves_no_empty_settings_behind_the_ansible_lock(template, tmp_path, env, home):
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text(json.dumps({
        "permissions": {"deny": ["Bash(ansible*)", "Bash(molecule*)"]},
        "hooks": {"PreToolUse": [ANSIBLE_LOCK]},
    }))
    target = make(template, tmp_path, env)
    s = settings(home)
    assert "permissions" not in s
    assert s["hooks"] == {"PreToolUse": [repo_rules_hook(target)]}


def test_setup_keeps_a_hook_file_of_that_name_it_did_not_link(template, tmp_path, env, home):
    hooks = home / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (hooks / "deny-ansible.py").write_text("# my own hook\n")
    make(template, tmp_path, env)
    assert (hooks / "deny-ansible.py").read_text() == "# my own hook\n"


def test_setup_sets_the_workflow_git_config(template, tmp_path, env):
    make(template, tmp_path, env)
    for key, value in (("pull.rebase", "true"), ("rebase.autoSquash", "true"),
                       ("push.autoSetupRemote", "true"), ("fetch.prune", "true"),
                       ("init.defaultBranch", "develop")):
        assert git("config", "--global", key, cwd=tmp_path, env=env) == value


def test_setup_hooks_the_zsh_fragment_in_once(template, tmp_path, env, home):
    target = make(template, tmp_path, env)
    zshrc = (home / ".zshrc").read_text()
    assert zshrc.count(f"source {target}/asf/shell/asf.zsh") == 1
    assert (target / "asf" / "shell" / "asf.zsh").is_file()


def test_setup_links_the_process_inbox_skill(template, tmp_path, env):
    target = make(template, tmp_path, env)
    link = target / ".claude" / "skills" / "process-inbox"
    assert link.is_symlink()
    assert (link / "SKILL.md").is_file()
    assert git("status", "--porcelain", cwd=target, env=env) == ""


# --- update ------------------------------------------------------------------


def update(template: Path, target: Path, tmp_path: Path, env: dict[str, str]) -> subprocess.CompletedProcess:
    return kasten(template, "update", str(target), cwd=tmp_path, env=env)


def first_line_replaced(path: Path, line: str) -> None:
    lines = path.read_text().splitlines(keepends=True)
    path.write_text(line + "\n" + "".join(lines[1:]))


def test_update_takes_the_templates_changes_and_commits(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n")
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "NEW.md").read_text() == "new\n"
    assert not (target / "asf" / "README.md").exists()
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "2"
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_gives_an_older_kasten_an_executable_gate(template, tmp_path, env):
    target = make(template, tmp_path, env)
    git("rm", "-q", "scripts/gate", cwd=target, env=env)
    git("commit", "-q", "-m", "a Kasten from before the gate", cwd=target, env=env)
    (template / "asf" / "LATER.md").write_text("later\n")
    commit(template, env, "a later template")
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert git("ls-files", "-s", "scripts/gate", cwd=target, env=env).startswith("100755")


def test_update_adds_new_seed_files_and_keeps_the_kastens_own(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "engineering" / "log.md").write_text("my log\n")
    git("commit", "-q", "-am", "log", cwd=target, env=env)
    (template / "asf" / "seed" / "engineering" / "log.md").write_text("fresh\n")
    (template / "asf" / "seed" / "glossary.md").write_text("glossary\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "engineering" / "log.md").read_text() == "my log\n"
    assert (target / "glossary.md").read_text() == "glossary\n"


def test_update_records_the_template_commit_as_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / ".asf-base").read_text() == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"


def test_update_without_a_base_replaces_asf_and_records_one(template, tmp_path, env):
    target = make(template, tmp_path, env)
    git("rm", "-q", ".asf-base", cwd=target, env=env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n")
    commit(target, env)
    (template / "asf" / "NEW.md").write_text("new\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text() == (template / "asf" / "AGENTS.md").read_text()
    assert (target / ".asf-base").read_text() == git("rev-parse", "HEAD", cwd=template, env=env) + "\n"


def test_update_keeps_the_kastens_own_changes_to_asf(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n")
    commit(target, env)
    (template / "asf" / "README.md").write_text("changed in the template\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text() == "changed in the Kasten\n"
    assert (target / "asf" / "README.md").read_text() == "changed in the template\n"


def test_update_merges_changes_to_different_lines_of_one_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    with (template / "asf" / "AGENTS.md").open("a") as agents:
        agents.write("appended in the template\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    merged = (target / "asf" / "AGENTS.md").read_text()
    assert merged.startswith("# changed in the Kasten\n")
    assert merged.endswith("appended in the template\n")
    assert "<<<<<<<" not in merged


def test_update_takes_new_and_deleted_files_and_keeps_the_kastens_new_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "MINE.md").write_text("mine\n")
    commit(target, env)
    (template / "asf" / "NEW.md").write_text("new\n")
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "MINE.md").read_text() == "mine\n"
    assert (target / "asf" / "NEW.md").read_text() == "new\n"
    assert not (target / "asf" / "README.md").exists()


def test_update_keeps_the_mode_of_a_new_executable(template, tmp_path, env):
    target = make(template, tmp_path, env)
    script = template / "asf" / "scripts" / "new.sh"
    script.write_text("#!/bin/sh\n")
    script.chmod(0o755)
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "scripts" / "new.sh").stat().st_mode & 0o111


def test_update_takes_a_mode_change_of_the_template(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "README.md").chmod(0o755)
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "README.md").stat().st_mode & 0o111


def test_update_takes_a_mode_change_on_a_merged_file(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    with (template / "asf" / "AGENTS.md").open("a") as agents:
        agents.write("appended in the template\n")
    (template / "asf" / "AGENTS.md").chmod(0o755)
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "AGENTS.md").read_text().startswith("# changed in the Kasten\n")
    assert (target / "asf" / "AGENTS.md").stat().st_mode & 0o111


def test_update_takes_a_file_whose_name_is_not_ascii(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "Übersicht.md").write_text("new\n")
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode == 0, result.stderr
    assert (target / "asf" / "Übersicht.md").read_text() == "new\n"


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
    (template / "asf" / "NEW.md").write_text("new\n")
    commit(template, env)
    assert update(template, target, tmp_path, env).returncode == 0
    git("reset", "-q", "--hard", "HEAD~1", cwd=template, env=env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "behind" in result.stderr
    assert (target / "asf" / "NEW.md").read_text() == "new\n"
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_leaves_markers_on_a_conflict_and_does_not_commit(template, tmp_path, env):
    target = make(template, tmp_path, env)
    first_line_replaced(target / "asf" / "AGENTS.md", "# changed in the Kasten")
    commit(target, env)
    first_line_replaced(template / "asf" / "AGENTS.md", "# changed in the template")
    commit(template, env)
    calls = (tmp_path / "claude.log").read_text()
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "asf/AGENTS.md" in result.stderr
    assert "<<<<<<< kasten" in (target / "asf" / "AGENTS.md").read_text()
    assert git("rev-list", "--count", "HEAD", cwd=target, env=env) == "2"
    assert (tmp_path / "claude.log").read_text() == calls


def test_update_reports_a_file_one_side_deleted_and_the_other_changed(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "README.md").write_text("changed in the Kasten\n")
    commit(target, env)
    (template / "asf" / "README.md").unlink()
    commit(template, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "asf/README.md" in result.stderr
    assert (target / "asf" / "README.md").read_text() == "changed in the Kasten\n"


def test_update_refuses_a_template_clone_with_uncommitted_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("new\n")
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "uncommitted" in result.stderr
    assert not (target / "asf" / "NEW.md").exists()
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_refuses_a_base_the_template_clone_does_not_have(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / ".asf-base").write_text("0" * 40 + "\n")
    commit(target, env)
    result = update(template, target, tmp_path, env)
    assert result.returncode != 0
    assert "git pull" in result.stderr
    assert git("status", "--porcelain", cwd=target, env=env) == ""


def test_update_after_an_export_only_moves_the_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n")
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
    (target / "AGENTS.md").write_text("changed\n")
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
    elsewhere.write_text("# kept\n")
    (home / ".claude").mkdir()
    (home / ".claude" / "CLAUDE.md").symlink_to(elsewhere)
    make(template, tmp_path, env)
    assert elsewhere.read_text() == "# kept\n"
    assert not (home / ".claude" / "CLAUDE.md").is_symlink()


# --- export ------------------------------------------------------------------


# The private name the tests leak, assembled so that it never stands whole in this
# file: the export checks asf/, and these tests are part of it.
LEAK = "secret" "-host"


def patterns(tmp_path: Path, *lines: str) -> Path:
    path = tmp_path / "leak-patterns.txt"
    path.write_text("\n".join(("# private names", "", *lines)) + "\n")
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


def test_export_gives_exactly_the_kastens_changes(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n")
    commit(target, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert git("status", "--porcelain", "--", "asf", cwd=template, env=env) == "M asf/AGENTS.md"


def test_export_replaces_what_was_there_but_keeps_git(template, tmp_path, env):
    (template / "stale.md").write_text("old\n")
    commit(template, env)
    target = make(template, tmp_path, env)
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert not (template / "stale.md").exists()
    assert (template / ".git").is_dir()


def test_export_leaves_caches_behind(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "scripts" / "__pycache__").mkdir()
    (target / "asf" / "scripts" / "__pycache__" / "kasten.pyc").write_text("x")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode == 0, result.stderr
    assert not (template / "asf" / "scripts" / "__pycache__").exists()


def test_export_stops_at_a_leak_and_writes_nothing(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "CONVENTIONS.md").write_text(f"ok\nssh to {LEAK.title()}.lan\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "asf/CONVENTIONS.md:2" in result.stderr
    assert LEAK in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == ""


def test_export_checks_the_template_root_files_too(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (target / "asf" / "template" / "README.md").write_text(f"by {LEAK}\n")
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
    (target / "asf" / "AGENTS.md").write_text("changed in the Kasten\n")
    (template / "asf" / "NOTE.md").write_text("draft\n")
    result = export(target, template, tmp_path, env, LEAK)
    assert result.returncode != 0
    assert "uncommitted" in result.stderr
    assert git("status", "--porcelain", cwd=template, env=env) == "?? asf/NOTE.md"


def test_export_refuses_when_the_template_moved_past_the_base(template, tmp_path, env):
    target = make(template, tmp_path, env)
    (template / "asf" / "NEW.md").write_text("from the other Kasten\n")
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
    (template / "asf" / "NEW.md").write_text("from the other Kasten\n")
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
