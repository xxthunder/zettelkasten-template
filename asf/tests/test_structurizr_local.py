"""structurizr-local.sh: the runtime it picks, the flags it passes, the arguments it refuses.

A fake docker or podman on a private PATH records its arguments, so no test starts a container.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ASF = Path(__file__).resolve().parents[1]
SCRIPT = ASF / "scripts" / "structurizr-local.sh"
TOOLS = ("bash", "id", "dirname")


def fake(bin_dir: Path, name: str, body: str) -> None:
    script = bin_dir / name
    script.write_text(f'#!{shutil.which("bash")}\n{body}\n')
    script.chmod(0o755)


def fake_path(tmp_path: Path, runtimes: tuple[str, ...], answers: bool) -> str:
    """A PATH with the tools the script needs, a recording fake for each runtime and for
    xdg-open, a curl that answers or not, and a sleep that returns at once."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in TOOLS:
        (bin_dir / tool).symlink_to(shutil.which(tool))
    for runtime in runtimes:
        fake(bin_dir, runtime, f'echo "{runtime} $*" > "{tmp_path}/called"')
    fake(bin_dir, "xdg-open", f'echo "xdg-open $*" > "{tmp_path}/opened"')
    fake(bin_dir, "curl", f'echo "$*" >> "{tmp_path}/polled"; exit {0 if answers else 7}')
    fake(bin_dir, "sleep", ":")
    return str(bin_dir)


def run(tmp_path: Path, *args: str, runtimes: tuple[str, ...] = ("podman",), answers: bool = True,
        browser: str | None = None) -> subprocess.CompletedProcess:
    env = {"PATH": fake_path(tmp_path, runtimes, answers)}
    if browser:
        env["BROWSER"] = browser
    return subprocess.run([shutil.which("bash"), str(SCRIPT), *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, env=env)


def called(tmp_path: Path) -> str:
    return (tmp_path / "called").read_text().strip()


USER = f"--user {os.getuid()}:{os.getgid()}"
MOUNT = f"-v {ASF / 'architecture'}:/usr/local/structurizr"


def test_podman_maps_the_calling_user_into_the_container(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 0
    assert called(tmp_path) == (f"podman run --rm --userns=keep-id {USER} -p 8080:8080 {MOUNT} "
                                "docker.io/structurizr/structurizr local")


def test_podman_wins_when_docker_is_there_too(tmp_path):
    """Where both exist, docker is most likely podman's alias."""
    run(tmp_path, runtimes=("docker", "podman"))
    assert called(tmp_path).startswith("podman run --rm --userns=keep-id ")


def test_docker_alone_runs_as_the_calling_user(tmp_path):
    run(tmp_path, runtimes=("docker",))
    assert called(tmp_path).startswith(f"docker run --rm {USER} -p 8080:8080 ")


def test_without_a_runtime_it_exits_1(tmp_path):
    result = run(tmp_path, runtimes=())
    assert result.returncode == 1
    assert "neither podman nor docker" in result.stderr


def test_the_port_is_passed_on(tmp_path):
    run(tmp_path, "--port=9090")
    assert " -p 9090:8080 " in called(tmp_path)


@pytest.mark.parametrize("port", ["0", "65536", "abc", ""])
def test_a_port_out_of_range_exits_4(tmp_path, port):
    result = run(tmp_path, f"--port={port}")
    assert result.returncode == 4
    assert "Usage:" in result.stderr
    assert not (tmp_path / "called").exists()


@pytest.mark.parametrize("port", ["1", "65535"])
def test_the_port_bounds_are_accepted(tmp_path, port):
    assert run(tmp_path, f"--port={port}").returncode == 0


def test_an_unknown_argument_exits_4(tmp_path):
    result = run(tmp_path, "--verbose")
    assert result.returncode == 4
    assert "Unknown argument: --verbose" in result.stderr


def test_the_runtime_files_are_ignored():
    assert ".structurizr/" in (ASF / "architecture" / ".gitignore").read_text().splitlines()


# ---------- --open: the browser opens once the viewer answers ----------

def test_open_opens_the_view_once_the_viewer_answers(tmp_path):
    result = run(tmp_path, "--open", "--port=9090")
    assert result.returncode == 0
    assert (tmp_path / "opened").read_text().strip() == "xdg-open http://localhost:9090"
    assert called(tmp_path).startswith("podman run ")


def test_open_prefers_the_browser_vs_code_sets(tmp_path):
    browser = tmp_path / "vscode-browser"
    fake(tmp_path, browser.name, f'echo "browser $*" > "{tmp_path}/opened"')
    run(tmp_path, "--open", browser=str(browser))
    assert (tmp_path / "opened").read_text().strip() == "browser http://localhost:8080"


def test_open_gives_up_after_120_seconds(tmp_path):
    result = run(tmp_path, "--open", answers=False)
    assert not (tmp_path / "opened").exists()
    assert len((tmp_path / "polled").read_text().splitlines()) == 120
    assert "did not answer within 120 seconds" in result.stderr


def test_without_open_no_browser_starts(tmp_path):
    run(tmp_path)
    assert not (tmp_path / "opened").exists()
    assert not (tmp_path / "polled").exists()



def test_no_view_lays_itself_out():
    """autoLayout recomputes a view on every render and drops a layout saved in the viewer."""
    dsl = (ASF / "architecture" / "workspace.dsl").read_text()
    assert "autoLayout" not in dsl
