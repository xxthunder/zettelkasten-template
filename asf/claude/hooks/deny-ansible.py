#!/usr/bin/env python3
"""PreToolUse hook: the agent runs no Ansible, anywhere.

Ansible is the operator's job. Every Ansible entry point can decrypt a vault and
changes live infrastructure, so a Bash command that invokes an Ansible
executable (or molecule, which runs Ansible) is denied — directly, behind a
wrapper (timeout, env, sudo), through a path (.venv/bin/ansible-playbook), or
inside another command (ssh host ..., devpod ssh ..., docker exec ..., bash -c).

Deny rules in settings.json only match the command as written; this hook reads
the whole text. Heredoc bodies are data (commit messages) and are skipped.
Naming a file such as ansible.cfg or a repo such as ansible-role-x is fine.
"""
import json
import re
import sys

EXECUTABLE = re.compile(
    r"(?:^|[\s'\"`;|&(/=])"
    r"(ansible(?:-(?:playbook|vault|inventory|galaxy|lint|pull|console|doc|config"
    r"|test|connection|runner|navigator|builder|creator))?|molecule)"
    r"(?=$|[\s'\"`;|&])"
)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?^\s*\2\s*$", re.S | re.M)


def main() -> int:
    payload = json.load(sys.stdin)
    if payload.get("tool_name") != "Bash":
        return 0
    command = (payload.get("tool_input") or {}).get("command") or ""
    match = EXECUTABLE.search(HEREDOC.sub("<<heredoc>>", command))
    if not match:
        return 0
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"`{match.group(1)}` is Ansible. The agent never runs Ansible — "
                    "not directly, not through ssh, devpod, docker or a wrapper. Hand "
                    "the exact command to the operator and wait for the output. To "
                    "search for the word, use the Grep tool instead of Bash."
                ),
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
