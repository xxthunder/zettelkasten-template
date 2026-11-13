"""structurizr-export.sh: the runtime it picks, the export command it runs, the arguments it refuses.

A fake docker, podman and curl on a private PATH record their calls, so no test starts a container.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ASF = Path(__file__).resolve().parents[1]
SCRIPT = ASF / "scripts" / "structurizr-export.sh"
TOOLS = ("bash", "id", "dirname", "mkdir")
NODE_PATH = "NODE_PATH=/home/pptruser/node_modules"
IMAGE = "ghcr.io/puppeteer/puppeteer"


def fake(bin_dir: Path, name: str, body: str) -> None:
    script = bin_dir / name
    script.write_text(f'#!{shutil.which("bash")}\n{body}\n')
    script.chmod(0o755)


def fake_path(tmp_path: Path, runtimes: tuple[str, ...], exit_code: int = 0) -> str:
    """A PATH with the tools the script needs, a recording fake for each runtime, a curl that
    answers, and a sleep that returns at once."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in TOOLS:
        (bin_dir / tool).symlink_to(shutil.which(tool))
    for runtime in runtimes:
        fake(bin_dir, runtime, f'echo "{runtime} $*" >> "{tmp_path}/called"; exit {exit_code}')
    fake(bin_dir, "curl", "exit 0")
    fake(bin_dir, "sleep", ":")
    return str(bin_dir)


def run(tmp_path: Path, *args: str, runtimes: tuple[str, ...] = ("podman",), exit_code: int = 0,
        cwd: Path | None = None) -> subprocess.CompletedProcess:
    env = {"PATH": fake_path(tmp_path, runtimes, exit_code)}
    return subprocess.run([shutil.which("bash"), str(SCRIPT), *args], capture_output=True, text=True,
                          stdin=subprocess.DEVNULL, env=env, cwd=cwd or tmp_path)


def log(tmp_path: Path) -> list[str]:
    return (tmp_path / "called").read_text().splitlines()


def podman_command(out: Path, port: int = 8080) -> str:
    return (f"podman run --rm --network host --userns=keep-id:uid=10042,gid=999 -e {NODE_PATH} "
            f"-v {ASF}/scripts:/scripts:ro -v {out}:/out {IMAGE} node /scripts/structurizr-export.js "
            f"http://localhost:{port}/workspace/1/diagrams /out")


def test_a_running_viewer_is_used_for_the_export(tmp_path):
    result = run(tmp_path, f"--out={tmp_path / 'out'}")
    assert result.returncode == 0
    assert log(tmp_path) == [podman_command(tmp_path / "out")]


def test_the_port_is_passed_on(tmp_path):
    run(tmp_path, f"--out={tmp_path / 'out'}", "--port=9090")
    assert log(tmp_path) == [podman_command(tmp_path / "out", 9090)]
    assert "http://localhost:9090/workspace/1/diagrams" in log(tmp_path)[0]


def test_a_relative_out_lands_under_the_current_directory(tmp_path):
    run(tmp_path, "--out=views", cwd=tmp_path)
    assert f"-v {tmp_path}/views:/out" in log(tmp_path)[0]


def test_a_missing_out_folder_is_created(tmp_path):
    run(tmp_path, f"--out={tmp_path / 'new' / 'views'}")
    assert (tmp_path / "new" / "views").is_dir()


def test_podman_wins_when_docker_is_there_too(tmp_path):
    run(tmp_path, f"--out={tmp_path / 'out'}", runtimes=("docker", "podman"))
    assert log(tmp_path) == [podman_command(tmp_path / "out")]


def test_docker_alone_runs_as_the_calling_user_with_a_writable_home(tmp_path):
    result = run(tmp_path, f"--out={tmp_path / 'out'}", runtimes=("docker",))
    assert result.returncode == 0
    assert log(tmp_path) == [
        f"docker run --rm --network host --user {os.getuid()}:{os.getgid()} -e HOME=/tmp -e {NODE_PATH} "
        f"-v {ASF}/scripts:/scripts:ro -v {tmp_path / 'out'}:/out {IMAGE} node /scripts/structurizr-export.js "
        "http://localhost:8080/workspace/1/diagrams /out"
    ]


def test_without_a_runtime_it_exits_1(tmp_path):
    result = run(tmp_path, f"--out={tmp_path / 'out'}", runtimes=())
    assert result.returncode == 1
    assert "neither podman nor docker" in result.stderr


def test_without_out_it_exits_4(tmp_path):
    result = run(tmp_path)
    assert result.returncode == 4
    assert "Usage:" in result.stderr


def test_an_unknown_argument_exits_4(tmp_path):
    result = run(tmp_path, f"--out={tmp_path / 'out'}", "--verbose")
    assert result.returncode == 4
    assert "Usage:" in result.stderr


@pytest.mark.parametrize("port", ["0", "65536", "abc"])
def test_a_port_out_of_range_exits_4(tmp_path, port):
    result = run(tmp_path, f"--out={tmp_path / 'out'}", f"--port={port}")
    assert result.returncode == 4
    assert "Usage:" in result.stderr


def test_the_exit_code_of_the_export_is_passed_on(tmp_path):
    result = run(tmp_path, f"--out={tmp_path / 'out'}", exit_code=3)
    assert result.returncode == 3


# --- a viewer of its own, when none answers (ZKK-018, Task 2) ---

REAL_SLEEP = shutil.which("sleep")


def local_command(port: int = 8080) -> str:
    return (f"podman run --rm --userns=keep-id --user {os.getuid()}:{os.getgid()} -p {port}:8080 "
            f"-v {ASF}/architecture:/usr/local/structurizr docker.io/structurizr/structurizr local")


def run_with_viewer(tmp_path: Path, failures: int, export_exit: int = 0) -> subprocess.CompletedProcess:
    """Run the export with a curl that fails its first `failures` calls and answers afterwards, and a
    podman whose `local` call stays up until it is terminated, then logs `stopped`."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in (*TOOLS, "cat"):
        (bin_dir / tool).symlink_to(shutil.which(tool))
    fake(bin_dir, "sleep", ":")
    # After its `failures` failed calls curl answers only once the fake viewer is up (its TERM trap is
    # set and `ready` exists), as a real viewer answers only after it started; `failures=0` is a
    # viewer that was running before the script began
    ready = "true" if failures == 0 else f'[ -e "{tmp_path}/ready" ]'
    fake(bin_dir, "curl",
         f'n=$(cat "{tmp_path}/count" 2>/dev/null || echo 0)\n'
         f'echo $((n + 1)) > "{tmp_path}/count"\n'
         f'[ "$n" -ge {failures} ] && {ready}')
    fake(bin_dir, "podman",
         f'echo "podman $*" >> "{tmp_path}/called"\n'
         'case "$*" in\n'
         '  *"structurizr local")\n'
         f'    trap \'echo stopped >> "{tmp_path}/called"; exit 0\' TERM\n'
         f'    : > "{tmp_path}/ready"\n'
         f'    while :; do {REAL_SLEEP} 1 & wait $!; done ;;\n'
         f'  *) exit {export_exit} ;;\n'
         'esac')
    return subprocess.run([shutil.which("bash"), str(SCRIPT), f"--out={tmp_path / 'out'}"],
                          capture_output=True, text=True, stdin=subprocess.DEVNULL,
                          env={"PATH": str(bin_dir)}, cwd=tmp_path, timeout=30)


def test_without_a_viewer_one_is_started_used_and_stopped(tmp_path):
    result = run_with_viewer(tmp_path, failures=1)
    assert result.returncode == 0
    assert log(tmp_path) == [local_command(), podman_command(tmp_path / "out"), "stopped"]


def test_a_running_viewer_is_left_running(tmp_path):
    result = run_with_viewer(tmp_path, failures=0)
    assert result.returncode == 0
    assert log(tmp_path) == [podman_command(tmp_path / "out")]


def test_a_viewer_that_never_answers_gives_up_after_120_tries(tmp_path):
    result = run_with_viewer(tmp_path, failures=10**9)
    assert result.returncode == 2
    assert "did not answer" in result.stderr
    assert log(tmp_path)[0] == local_command()
    assert not any("structurizr-export.js" in line for line in log(tmp_path))
    assert log(tmp_path)[-1] == "stopped"


def test_the_started_viewer_is_stopped_when_the_export_fails(tmp_path):
    result = run_with_viewer(tmp_path, failures=1, export_exit=3)
    assert result.returncode == 3
    assert log(tmp_path)[-1] == "stopped"
