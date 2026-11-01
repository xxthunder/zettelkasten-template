"""`asf/scripts/lint.sh`: the areas it checks are the Kasten's, found on disk.

An area is a top-level folder with a `README.md` hub. The template's own folders
and the meta folders are never areas, so the same script lints every Kasten
without a list of areas in it.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import ASF

LINT = ASF / "scripts" / "lint.sh"
NOTE = "---\ntitle: \"{title}\"\ncreated: 2026-01-01\ntags: [test]\ntype: {type}\n---\n\n# {title}\n\n[← Hub](README.md)\n\nBody.\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def hub(kasten: Path, area: str, *notes: str) -> None:
    links = "".join(f"- [{n}]({n}.md)\n" for n in notes)
    write(kasten / area / "README.md", NOTE.format(title=area, type=area) + links)


def lint(kasten: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(LINT)], cwd=str(kasten), capture_output=True, text=True)


def test_a_folder_with_a_hub_is_an_area(tmp_path):
    hub(tmp_path, "garden", "roses")
    write(tmp_path / "garden" / "roses.md", "# no frontmatter\n")
    result = lint(tmp_path)
    assert "Missing frontmatter: garden/roses.md" in result.stdout
    assert "Done: 1 errors" in result.stdout


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


# ---------- architecture: the Structurizr workspace is validated ----------

VALID_DSL = 'workspace "T" {\n    model {\n        a = person "A"\n    }\n    views {\n        systemLandscape {\n            include *\n        }\n    }\n}\n'
needs_docker = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")


def no_docker_path(tmp_path: Path) -> str:
    """A PATH with the tools lint.sh needs, and no docker."""
    bin_dir = tmp_path / "bin-no-docker"
    bin_dir.mkdir()
    for tool in ("bash", "head", "grep", "find", "sort", "sed", "wc", "tr", "xargs", "uniq", "basename", "dirname", "cat"):
        found = shutil.which(tool)
        if found:
            (bin_dir / tool).symlink_to(found)
    return str(bin_dir)


@needs_docker
def test_a_valid_workspace_passes(tmp_path):
    write(tmp_path / "asf" / "architecture" / "workspace.dsl", VALID_DSL)
    result = lint(tmp_path)
    assert "Architecture: asf/architecture/workspace.dsl is valid" in result.stdout
    assert "Done: 0 errors, 0 warnings" in result.stdout


@needs_docker
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
    result = subprocess.run([shutil.which("bash"), str(LINT)], cwd=str(tmp_path), capture_output=True, text=True,
                            env={"PATH": no_docker_path(tmp_path)})
    assert "Architecture not validated: docker is not installed" in result.stdout
    assert "Done: 0 errors, 1 warnings" in result.stdout
