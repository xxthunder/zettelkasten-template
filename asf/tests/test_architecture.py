"""`asf/architecture/workspace.dsl`: the structure of the C4 model of the closed loop.

The model is exported to JSON with Structurizr and the elements and views are checked
by name, so a rename or a lost view fails here, not in a reader's head.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from conftest import ASF

pytestmark = pytest.mark.skipif(shutil.which("docker") is None, reason="docker is not installed")

IMAGE = "docker.io/structurizr/structurizr:latest"

AGENT_ROLES = {"Session", "Tester", "Implementer", "Task reviewer", "Final reviewer"}


@pytest.fixture(scope="module")
def workspace(tmp_path_factory) -> dict:
    out = tmp_path_factory.mktemp("structurizr")
    subprocess.run(
        [
            "docker", "run", "--rm", "--user", f"{os.getuid()}:{os.getgid()}",
            "-v", f"{ASF / 'architecture'}:/workspace:ro", "-v", f"{out}:/out",
            IMAGE, "export", "-w", "/workspace/workspace.dsl", "-f", "json", "-o", "/out",
        ],
        check=True, capture_output=True, text=True,
    )
    return json.loads((out / "workspace.json").read_text())


def systems(ws: dict) -> list[dict]:
    return ws["model"]["softwareSystems"]


def find(items: list[dict], name: str, what: str) -> dict:
    for item in items:
        if item["name"] == name:
            return item
    raise AssertionError(f"no {what} named {name!r}; found {sorted(i['name'] for i in items)}")


def asf(ws: dict) -> dict:
    return find(systems(ws), "Agentic Software Forge", "software system")


def container(ws: dict, name: str) -> dict:
    return find(asf(ws).get("containers", []), name, "container of the ASF")


def components(ws: dict, name: str) -> list[dict]:
    return container(ws, name).get("components", [])


def names(items: list[dict]) -> set[str]:
    return {item["name"] for item in items}


def all_relationships(ws: dict) -> dict[str, dict]:
    """Every model relationship by id, wherever it sits."""
    elements = list(ws["model"].get("people", []))
    for system in systems(ws):
        elements.append(system)
        for cont in system.get("containers", []):
            elements.append(cont)
            elements.extend(cont.get("components", []))
    return {r["id"]: r for e in elements for r in e.get("relationships", [])}


def element_names(ws: dict) -> dict[str, str]:
    elements = list(ws["model"].get("people", []))
    for system in systems(ws):
        elements.append(system)
        for cont in system.get("containers", []):
            elements.append(cont)
            elements.extend(cont.get("components", []))
    return {e["id"]: e["name"] for e in elements}


def test_the_context_shows_the_asf_and_its_six_partners(workspace):
    assert names(workspace["model"].get("people", [])) == {"Author"}
    assert names(systems(workspace)) == {
        "Agentic Software Forge", "Provisioner", "LLM", "SCM", "CI server", "Issue tracker",
    }


def test_the_asf_has_five_containers(workspace):
    assert names(asf(workspace).get("containers", [])) == {
        "Coding Agent", "Harness", "Kasten", "Repository checkout", "Dev container",
    }


def test_the_coding_agent_runs_in_five_roles(workspace):
    assert names(components(workspace, "Coding Agent")) == AGENT_ROLES


def test_the_harness_holds_the_plugins(workspace):
    parts = components(workspace, "Harness")
    assert names(parts) == {"xxthunder-dev-skills", "superpowers", "Jira skill", "MCP servers"}
    planned = [p["name"] for p in parts if "Planned" in p.get("tags", "").split(",")]
    assert planned == [], f"components still tagged Planned: {planned}"
    description = find(parts, "xxthunder-dev-skills", "component of the Harness")["description"]
    assert "closed-loop" in description
    assert "loop.py" in description


def test_the_kasten_holds_contracts_board_log_rubric_and_registry(workspace):
    assert names(components(workspace, "Kasten")) == {
        "Contracts", "Board", "Logbook", "General rubric", "Repository registry",
    }


def test_the_views_are_the_c4_cut(workspace):
    views = workspace["views"]
    assert set(k["key"] for k in views.get("systemContextViews", [])) == {"Context"}
    assert set(k["key"] for k in views.get("containerViews", [])) == {"Containers"}
    component_views = {v["key"]: v for v in views.get("componentViews", [])}
    assert set(component_views) == {"CodingAgent", "Harness", "Kasten"}
    for key, container_name in {"CodingAgent": "Coding Agent", "Harness": "Harness", "Kasten": "Kasten"}.items():
        assert component_views[key]["containerId"] == container(workspace, container_name)["id"], key
    assert set(v["key"] for v in views.get("dynamicViews", [])) == {"Loop", "Unit", "Dispute"}


def dynamic_view(ws: dict, key: str) -> dict:
    return find([dict(v, name=v["key"]) for v in ws["views"].get("dynamicViews", [])], key, "dynamic view")


def roles_in(ws: dict, view: dict) -> set[str]:
    label = element_names(ws)
    return {label[e["id"]] for e in view["elements"]}


def test_the_loop_follows_one_item_at_container_level(workspace):
    loop = dynamic_view(workspace, "Loop")
    assert loop["elementId"] == asf(workspace)["id"]


def test_the_stop_is_an_edge_from_the_session_to_the_author(workspace):
    label = element_names(workspace)
    stops = [
        r["description"]
        for r in all_relationships(workspace).values()
        if label[r["sourceId"]] == "Session" and label[r["destinationId"]] == "Author"
    ]
    assert any(text.startswith("Stop") for text in stops), f"edges from Session to Author: {stops}"


def test_the_unit_follows_the_main_path_through_the_roles(workspace):
    unit = dynamic_view(workspace, "Unit")
    assert unit["elementId"] == container(workspace, "Coding Agent")["id"]
    assert names(components(workspace, "Coding Agent")) == AGENT_ROLES
    assert {"Session", "Tester", "Implementer", "Task reviewer"} <= roles_in(workspace, unit)


def test_the_dispute_goes_from_the_implementer_to_a_fresh_tester(workspace):
    dispute = dynamic_view(workspace, "Dispute")
    assert dispute["elementId"] == container(workspace, "Coding Agent")["id"]
    assert {"Session", "Tester", "Implementer"} <= roles_in(workspace, dispute)
