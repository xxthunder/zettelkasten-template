#!/usr/bin/env python3
"""Make a new Kasten from the template, set a machine up for a Kasten, update one.

    kasten.py new <target> [--remote <url>]
        Run from a clone of the template. Copies asf/ and the files in asf/seed/
        into <target>, which must not exist or be empty, makes the first commit on
        `develop`, sets `origin` when a remote is given, and runs `setup` there.
        It never pushes.

    kasten.py setup
        Run from a Kasten. Points the user's Claude Code, git and zsh at it:
        ~/.claude/CLAUDE.md imports the shared and the Kasten's own global
        instructions; the claude CLI adds the shared marketplaces and installs the
        shared plugins, naming any it could not install; ~/.claude/settings.json
        gets the shared plugins, marketplaces,
        hook and deny rules, and the logbook, learnings and board variables for
        this Kasten — every other setting stays as it is; the hook is linked into
        ~/.claude/hooks/; the workflow's git settings go into the global config;
        ~/.zshrc sources asf/shell/asf.zsh; the process-inbox skill is linked into
        the Kasten's .claude/skills/. A file it replaces is kept as
        <name>.bak-<timestamp>, and it says so. Running it again changes nothing.

    kasten.py update <kasten>
        Run from a clone of the template, after `git pull` there. Replaces the
        Kasten's asf/ with the template's, adds seed files the Kasten does not have
        yet — never overwrites one it has — runs `setup` and commits. A Kasten with
        uncommitted changes is refused.

    kasten.py export <dest> --patterns <file>
        Run from the Kasten the template is made from. Checks asf/ against the
        patterns in <file> — one regular expression per line, case-insensitive,
        `#` starts a comment — and stops at the first leak, naming file and line,
        with nothing written. Otherwise <dest> holds asf/ and, in its root, the
        files of asf/template/; whatever else was there goes, a .git stays. It
        never commits. The patterns file names what must not leak, so it lives
        outside asf/.

Standard library only: a fresh machine has python3 before it has anything else.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IGNORED = shutil.ignore_patterns(".venv", "__pycache__", ".pytest_cache")
GIT_CONFIG = {
    "pull.rebase": "true",
    "rebase.autoSquash": "true",
    "push.autoSetupRemote": "true",
    "fetch.prune": "true",
    "init.defaultBranch": "develop",
}
GENERATED = "<!-- Written by asf/scripts/kasten.py setup. Edit the imported files instead. -->"


class Refused(Exception):
    """A precondition does not hold; nothing has been changed."""


def git(*args: str, cwd: Path) -> str:
    result = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)
    if result.returncode != 0:
        raise Refused(f"git {' '.join(args)} failed in {cwd}: {result.stderr.strip()}")
    return result.stdout.strip()


def write_if_changed(path: Path, text: str) -> None:
    if path.is_file() and path.read_text() == text:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def back_up(path: Path) -> Path:
    """Move path aside as <name>.bak-<timestamp> and say where it went."""
    backup = path.with_name(f"{path.name}.bak-{time.strftime('%Y%m%d%H%M%S')}")
    path.rename(backup)
    print(f"Kept the old {path} as {backup}")
    return backup


def link(path: Path, target: Path) -> None:
    """Make path a symlink to target; a file in its place is kept as a backup."""
    if path.is_symlink() and path.resolve() == target.resolve():
        return
    if path.is_symlink():
        path.unlink()
    elif path.exists():
        back_up(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(target)


def seed_files(source: Path) -> list[Path]:
    seed = source / "asf" / "seed"
    return sorted(p.relative_to(seed) for p in seed.rglob("*") if p.is_file())


def copy_asf(source: Path, target: Path) -> None:
    if (target / "asf").exists():
        shutil.rmtree(target / "asf")
    shutil.copytree(source / "asf", target / "asf", ignore=IGNORED)


def copy_missing_seed(source: Path, target: Path) -> None:
    for relative in seed_files(source):
        destination = target / relative
        if not destination.exists():
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / "asf" / "seed" / relative, destination)


# --- new ---------------------------------------------------------------------


def new(target: Path, remote: str | None) -> None:
    target = target.resolve()
    if target.exists() and any(target.iterdir()):
        raise Refused(f"{target} is not empty — a new Kasten needs an empty or new directory")
    target.mkdir(parents=True, exist_ok=True)
    copy_asf(ROOT, target)
    copy_missing_seed(ROOT, target)
    write_if_changed(
        target / ".claude" / "settings.json",
        json.dumps({"autoMemoryDirectory": str(target / "memory")}, indent=2) + "\n",
    )
    git("init", "-q", "-b", "develop", cwd=target)
    git("add", "-A", cwd=target)
    git("commit", "-q", "-m", "chore: new Kasten from the template", cwd=target)
    if remote:
        git("remote", "add", "origin", remote, cwd=target)
    setup(target)
    print(f"New Kasten at {target}" + (f", origin {remote}" if remote else ", no remote yet"))


# --- setup -------------------------------------------------------------------


def merge_settings(current: dict, shared: dict, kasten: Path, remote: str | None) -> dict:
    merged = json.loads(json.dumps(current))
    merged.setdefault("enabledPlugins", {}).update(shared.get("enabledPlugins", {}))
    merged.setdefault("extraKnownMarketplaces", {}).update(shared.get("extraKnownMarketplaces", {}))
    deny = merged.setdefault("permissions", {}).setdefault("deny", [])
    deny.extend(rule for rule in shared.get("permissions", {}).get("deny", []) if rule not in deny)
    for event, entries in shared.get("hooks", {}).items():
        present = merged.setdefault("hooks", {}).setdefault(event, [])
        present.extend(entry for entry in entries if entry not in present)
    environment = merged.setdefault("env", {})
    for prefix in ("LOGBOOK", "LEARNINGS", "BOARD"):
        environment[f"{prefix}_PATH"] = str(kasten)
        if remote:
            environment[f"{prefix}_REMOTE"] = remote
    return merged


def install_plugins(shared: dict) -> None:
    """Add the shared marketplaces and install the shared plugins with the claude CLI.

    Left to itself, Claude Code installs them in the background over its first starts;
    explicitly, the first start has them all. A plugin that fails is named, not fatal.
    """
    cli = shutil.which("claude")
    if cli is None:
        print("claude is not on the PATH, so no plugins were installed — run setup again once it is")
        return
    commands = [["plugin", "marketplace", "add", spec["source"]["repo"]]
                for spec in shared.get("extraKnownMarketplaces", {}).values()]
    commands += [["plugin", "install", plugin]
                 for plugin, enabled in shared.get("enabledPlugins", {}).items() if enabled]
    for command in commands:
        result = subprocess.run([cli, *command], capture_output=True, text=True)
        if result.returncode != 0:
            said = (result.stdout + result.stderr).strip().splitlines()
            print(f"Could not run claude {' '.join(command)}: {said[-1] if said else 'no output'}")


def setup(kasten: Path) -> None:
    kasten = kasten.resolve()
    home = Path(os.environ["HOME"])
    claude = home / ".claude"
    remote = None
    origin = subprocess.run(["git", "remote", "get-url", "origin"], cwd=str(kasten),
                            capture_output=True, text=True)
    if origin.returncode == 0:
        remote = origin.stdout.strip()

    instructions = claude / "CLAUDE.md"
    text = f"{GENERATED}\n\n@{kasten}/asf/claude/CLAUDE.md\n\n@{kasten}/claude/CLAUDE.md\n"
    if instructions.is_symlink():
        instructions.unlink()
    elif instructions.is_file() and GENERATED not in instructions.read_text():
        back_up(instructions)
        print(f"  It is no longer loaded; move what still applies into {kasten}/claude/CLAUDE.md")
    write_if_changed(instructions, text)

    # The CLI rewrites the user settings, so they are read and merged after it ran.
    shared = json.loads((kasten / "asf" / "claude" / "settings.json").read_text())
    install_plugins(shared)
    settings_path = claude / "settings.json"
    current = json.loads(settings_path.read_text()) if settings_path.is_file() else {}
    merged = merge_settings(current, shared, kasten, remote)
    if merged != current:
        write_if_changed(settings_path, json.dumps(merged, indent=2, ensure_ascii=False) + "\n")

    for hook in sorted((kasten / "asf" / "claude" / "hooks").iterdir()):
        link(claude / "hooks" / hook.name, hook)

    for key, value in GIT_CONFIG.items():
        present = subprocess.run(["git", "config", "--global", key], capture_output=True, text=True)
        if present.stdout.strip() != value:
            git("config", "--global", key, value, cwd=kasten)

    zshrc = home / ".zshrc"
    line = f"source {kasten}/asf/shell/asf.zsh"
    existing = zshrc.read_text() if zshrc.is_file() else ""
    if line not in existing.splitlines():
        separator = "" if not existing or existing.endswith("\n") else "\n"
        write_if_changed(zshrc, f"{existing}{separator}{line}\n")

    for skill in sorted((kasten / "asf" / "skills").iterdir()):
        link(kasten / ".claude" / "skills" / skill.name, Path("../../asf/skills") / skill.name)


# --- update ------------------------------------------------------------------


def update(target: Path) -> None:
    target = target.resolve()
    if not (target / "asf").is_dir() or not (target / "AGENTS.md").is_file():
        raise Refused(f"{target} is no Kasten — it has no asf/ and AGENTS.md")
    if git("status", "--porcelain", cwd=target):
        raise Refused(f"{target} has uncommitted changes — commit or stash them first")
    copy_asf(ROOT, target)
    copy_missing_seed(ROOT, target)
    setup(target)
    git("add", "-A", cwd=target)
    if not git("status", "--porcelain", cwd=target):
        print(f"{target} is up to date with the template")
        return
    revision = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT),
                              capture_output=True, text=True).stdout.strip() or "unknown"
    git("commit", "-q", "-m", f"chore(asf): update from the template ({revision})", cwd=target)
    print(f"Updated {target} from the template ({revision}); push it when you are ready")


# --- export ------------------------------------------------------------------


def read_patterns(path: Path) -> list[re.Pattern]:
    if not path.is_file():
        raise Refused(f"no patterns file at {path} — the export needs the list of what must not leak")
    lines = (line.strip() for line in path.read_text().splitlines())
    return [re.compile(line, re.IGNORECASE) for line in lines if line and not line.startswith("#")]


def leaks(source: Path, checks: list[re.Pattern]) -> list[str]:
    found = []
    for path in sorted((source / "asf").rglob("*")):
        relative = path.relative_to(source)
        if not path.is_file() or any(part in {".venv", "__pycache__", ".pytest_cache"} for part in relative.parts):
            continue
        try:
            lines = path.read_text().splitlines()
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(lines, 1):
            for check in checks:
                if check.search(line):
                    found.append(f"{relative}:{number}: matches '{check.pattern}'")
    return found


def export(dest: Path, patterns: Path) -> None:
    dest = dest.resolve()
    found = leaks(ROOT, read_patterns(patterns.resolve()))
    if found:
        raise Refused("leak check failed, nothing exported:\n  " + "\n  ".join(found))
    dest.mkdir(parents=True, exist_ok=True)
    for entry in dest.iterdir():
        if entry.name == ".git":
            continue
        shutil.rmtree(entry) if entry.is_dir() and not entry.is_symlink() else entry.unlink()
    copy_asf(ROOT, dest)
    for entry in sorted((ROOT / "asf" / "template").iterdir()):
        shutil.copy2(entry, dest / entry.name)
    print(f"Exported the template to {dest}; leak check clean — review and commit it there")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="kasten.py", description=__doc__.split("\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    make = commands.add_parser("new", help="make a new Kasten from this template")
    make.add_argument("target", type=Path)
    make.add_argument("--remote")
    commands.add_parser("setup", help="set this machine up for this Kasten")
    refresh = commands.add_parser("update", help="update a Kasten from this template")
    refresh.add_argument("kasten", type=Path)
    publish = commands.add_parser("export", help="export this Kasten's asf/ as the template")
    publish.add_argument("dest", type=Path)
    publish.add_argument("--patterns", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "new":
            new(args.target, args.remote)
        elif args.command == "setup":
            setup(ROOT)
        elif args.command == "export":
            export(args.dest, args.patterns)
        else:
            update(args.kasten)
    except Refused as refusal:
        print(f"kasten.py: {refusal}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
