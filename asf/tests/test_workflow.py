from pathlib import Path

WORKFLOW = Path(__file__).parent.parent / "template" / ".github" / "workflows" / "gate.yml"


def _uses_values():
    values = []
    for line in WORKFLOW.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            stripped = stripped[2:].strip()
        if stripped.startswith("uses:"):
            values.append(stripped[len("uses:"):].strip())
    return values


def test_the_template_workflow_uses_node24_actions():
    # Node.js 20 is deprecated on GitHub runners. setup-uv publishes no major
    # tags since v8, so its full version is pinned.
    uses = _uses_values()
    assert "actions/checkout@v7" in uses
    assert "astral-sh/setup-uv@v10.3.3" in uses
    assert not [u for u in uses if u.startswith("actions/checkout@v4")]
    assert not [u for u in uses if u.startswith("astral-sh/setup-uv@v6")]
