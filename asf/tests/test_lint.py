"""`asf/scripts/lint.sh`: the areas it checks are the Kasten's, found on disk.

An area is a top-level folder with a `README.md` hub. The template's own folders
and the meta folders are never areas, so the same script lints every Kasten
without a list of areas in it.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import ASF, WINDOWS

LINT = ASF / "scripts" / "lint.sh"
NOTE = "---\ntitle: \"{title}\"\ncreated: 2026-01-01\ntags: [test]\ntype: {type}\n---\n\n# {title}\n\n[← Hub](README.md)\n\nBody.\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def hub(kasten: Path, area: str, *notes: str) -> None:
    links = "".join(f"- [{n}]({n}.md)\n" for n in notes)
    write(kasten / area / "README.md", NOTE.format(title=area, type=area) + links)


def lint(kasten: Path) -> subprocess.CompletedProcess:
    return subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(kasten), capture_output=True, text=True, encoding="utf-8")


def test_a_folder_with_a_hub_is_an_area(tmp_path):
    hub(tmp_path, "garden", "roses")
    write(tmp_path / "garden" / "roses.md", "# no frontmatter\n")
    result = lint(tmp_path)
    assert "Missing frontmatter: garden/roses.md" in result.stdout
    assert "Done: 1 errors" in result.stdout


def test_lint_exits_non_zero_when_it_finds_errors(tmp_path):
    hub(tmp_path, "garden", "roses")
    write(tmp_path / "garden" / "roses.md", "# no frontmatter\n")
    assert lint(tmp_path).returncode == 1


def test_lint_exits_zero_when_it_finds_no_errors(tmp_path):
    hub(tmp_path, "garden", "roses")
    write(tmp_path / "garden" / "roses.md", NOTE.format(title="roses", type="garden"))
    assert lint(tmp_path).returncode == 0


def test_a_folder_without_a_hub_is_no_area(tmp_path):
    write(tmp_path / "recipes" / "loose.md", "# no frontmatter\n")
    result = lint(tmp_path)
    assert "recipes" not in result.stdout
    assert "Done: 0 errors, 0 warnings" in result.stdout


def test_template_and_meta_folders_are_never_areas(tmp_path):
    for folder in ("asf", "docs", "inbox", "memory", "templates", "scripts"):
        write(tmp_path / folder / "README.md", "# no frontmatter\n")
    result = lint(tmp_path)
    assert "Done: 0 errors, 0 warnings" in result.stdout


def test_an_orphan_in_a_found_area_is_reported(tmp_path):
    hub(tmp_path, "garden")
    write(tmp_path / "garden" / "trip.md", NOTE.format(title="trip", type="garden"))
    result = lint(tmp_path)
    assert "Orphaned (no incoming links): garden/trip.md" in result.stdout


def test_a_broken_link_in_a_found_area_is_reported(tmp_path):
    hub(tmp_path, "learnings", "claim")
    write(tmp_path / "learnings" / "claim.md",
          NOTE.format(title="claim", type="learning") + "\n[gone](gone.md)\n")
    result = lint(tmp_path)
    assert "Broken link in learnings/claim.md → gone.md" in result.stdout


def test_the_tag_report_lists_the_tags(tmp_path):
    """grep -P needs a UTF-8 locale; Git Bash has none unless the script sets one."""
    hub(tmp_path, "garden", "roses")
    write(tmp_path / "garden" / "roses.md",
          NOTE.format(title="roses", type="garden").replace("tags: [test]", "tags: [alpha, beta]"))
    env = {k: v for k, v in os.environ.items() if k not in ("LC_ALL", "LANG", "LC_CTYPE")}
    result = subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(tmp_path), capture_output=True, text=True,
                            encoding="utf-8", env=env)
    report = result.stdout.split("--- Tag Report ---", 1)[1]
    assert "alpha" in report
    assert "beta" in report


# ---------- architecture: the Structurizr workspace is validated ----------

VALID_DSL = 'workspace "T" {\n    model {\n        a = person "A"\n    }\n    views {\n        systemLandscape {\n            include *\n        }\n    }\n}\n'
needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")
linux_only = pytest.mark.skipif(WINDOWS, reason="the architecture check runs on Linux only (ZKK-023)")


def no_docker_path(tmp_path: Path) -> str:
    """A PATH with the tools lint.sh needs, and no docker."""
    bin_dir = tmp_path / "bin-no-docker"
    bin_dir.mkdir()
    for tool in ("bash", "head", "grep", "find", "sort", "sed", "wc", "tr", "xargs", "uniq", "basename", "dirname", "cat"):
        found = shutil.which(tool)
        if found:
            if WINDOWS:
                # Symlinks need a privilege on Windows; a wrapper script does the same job
                wrapper = bin_dir / tool
                wrapper.write_text(f'#!/bin/sh\nexec "{Path(found).as_posix()}" "$@"\n',
                                   encoding="utf-8", newline="\n")
            else:
                (bin_dir / tool).symlink_to(found)
    return str(bin_dir)


@needs_docker
@linux_only
def test_a_valid_workspace_passes(tmp_path):
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL)
    result = lint(tmp_path)
    assert "Architecture: asf/architecture/workspace.dsl is valid" in result.stdout
    assert "Done: 0 errors, 0 warnings" in result.stdout


@needs_docker
@linux_only
def test_an_invalid_workspace_is_an_error(tmp_path):
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL.replace("person", "persn"))
    result = lint(tmp_path)
    assert "Invalid architecture: asf/architecture/workspace.dsl" in result.stdout
    assert "Done: 1 errors" in result.stdout


def test_a_kasten_without_a_workspace_skips_the_check(tmp_path):
    result = lint(tmp_path)
    assert "workspace.dsl" not in result.stdout
    assert "Done: 0 errors, 0 warnings" in result.stdout


def test_without_docker_the_check_is_a_warning_not_an_error(tmp_path):
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL)
    result = subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8",
                            env={"PATH": no_docker_path(tmp_path)})
    # On Windows the Linux-only warning comes first, whatever is on PATH (ZKK-023)
    expected = "the check runs on Linux only" if WINDOWS else "docker is not installed"
    assert f"Architecture not validated: {expected}" in result.stdout
    assert "Done: 0 errors, 1 warnings" in result.stdout


@linux_only
def test_the_default_image_names_its_registry(tmp_path):
    """Podman resolves no short image names unless the machine configures a registry."""
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL)
    path = no_docker_path(tmp_path)
    called = tmp_path / "docker-args"
    docker = Path(path) / "docker"
    docker.write_text(f'#!{Path(shutil.which("bash")).as_posix()}\necho "$@" > {called.as_posix()}\n', encoding="utf-8", newline="\n")
    docker.chmod(0o755)
    subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(tmp_path), capture_output=True, text=True, encoding="utf-8",
                   env={"PATH": path})
    assert " docker.io/structurizr/structurizr:latest " in called.read_text(encoding="utf-8")


@pytest.mark.skipif(not WINDOWS, reason="the architecture check is skipped on Windows only (ZKK-023)")
def test_on_windows_the_architecture_check_is_skipped(tmp_path):
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL)
    path = no_docker_path(tmp_path)
    docker = Path(path) / "docker"
    docker.write_text(f'#!{Path(shutil.which("bash")).as_posix()}\nexit 0\n', encoding="utf-8", newline="\n")
    docker.chmod(0o755)
    result = subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(tmp_path), capture_output=True, text=True,
                            encoding="utf-8", env={"PATH": path})
    warnings = [line for line in result.stdout.splitlines() if "Linux only" in line]
    assert len(warnings) == 1
    assert "is valid" not in result.stdout
    assert result.returncode == 0
