# Agentic Software Forge (ASF)

The Agentic Software Forge is a way of building software with AI agents: the same workflow on
every machine, so it is learned and maintained once. What is reproducible is the **how**, not
the **what** — each Kasten holds its own notes, repos and decisions; the workflows, skills and
rules are the same everywhere.

## Four pillars

- **Kasten structure** — this folder. A backlog per repo, a log across repos, a board of
  what comes next and what is in progress, learnings, and the agent's memory, each with its contract in
  [AGENTS.md](AGENTS.md) and its rules in [CONVENTIONS.md](CONVENTIONS.md).
- **Agentic skills** — the Claude Code skills that work this structure:
  [xxthunder-agentic-skills](https://github.com/xxthunder/xxthunder-agentic-skills)
  (`backlog-ops`, `logbook`, `learnings`, `next`, `commit-helper`, `design-record`, …).
- **Machine roles** — the tools of the machine, installed with admin rights by its
  provisioning, not by this template:
  [ansible-role-dev-stack](https://github.com/xxthunder/ansible-role-dev-stack).
- **Kasten template** — [zettelkasten-template](https://github.com/xxthunder/zettelkasten-template):
  the how as a public repository a new Kasten is made from.

## The work loop

Pull an item — its card moves to *In Progress* on the board → log the start → work in a
worktree on a feature branch → close the item — its card leaves the board → log the end.
Every step is a skill, and every step writes into a repo, never into a chat. The log is
optional; the board works without it.

Inside the worktree the work runs as a **closed loop**: an implementer subagent writes the
test and the code for each task, a reviewer subagent judges the diff against the
repository's rubric, and the loop ends only when the repository's gate is green — the
gate it names, often `scripts/gate`, or else the one derived from its CI. The author confirms an evidence package in the pull request
instead of reading the diff. The contract is `Closed loop` in [AGENTS.md](AGENTS.md); the
architecture is a Structurizr workspace in
[architecture/workspace.dsl](architecture/workspace.dsl).

## What lives here

`asf/` is the template's part of a Kasten, the same in every Kasten. What is particular to one
Kasten goes into its own files in its root — its own `AGENTS.md` imports
[AGENTS.md](AGENTS.md) from here, its own `CONVENTIONS.md` adds to
[CONVENTIONS.md](CONVENTIONS.md).

- [AGENTS.md](AGENTS.md) — the agent's roles and the contracts for learnings, log, the
  board and the closed loop
- [rubric.md](rubric.md) — what a reviewer in the closed loop judges in every repository
- `architecture/workspace.dsl` — the closed loop as a Structurizr workspace; `lint.sh`
  validates it, and `scripts/structurizr-local.sh [--port=<port>] [--open]` shows its views
  on http://localhost:8080 with podman or docker (Ctrl+C stops it); `--open` opens them in
  the browser once the viewer answers. Arrange a view in the viewer's edit mode and save it
  there. The viewer writes the model
  and the layout of the views to `workspace.json`, which is committed together with
  `workspace.dsl`. When only its `lastModifiedDate` changed, discard that change
- [CONVENTIONS.md](CONVENTIONS.md) — principles, file names, frontmatter, linking, language
- `templates/` — a template per note type: `learning`, `literature`, `engineering`
- `scripts/` — `lint.sh`, `review.sh`, `new-zettel.sh`, and `kasten.py`, which makes a new
  Kasten (`new`), sets a machine up for one (`setup`) and updates one (`update`); its tests
  are in `tests/` (`cd asf && uv run --group dev pytest`)
- `claude/` — the global instructions, the shared part of the user settings (plugins,
  marketplaces) and the `repo-rules` hook, which has a session read a neighbour
  repository's rules before its first call there; `setup` points `~/.claude` at them,
  registers the hook and installs the plugins
- `shell/asf.zsh` — `PATH` for `claude` and `uv`, and `claude-tmux`; `setup` sources it from
  `~/.zshrc`
- `skills/` — the Kasten's own skills (`process-inbox`); `setup` links them into
  `.claude/skills/`
- `seed/` — the files a new Kasten starts with; afterwards they are the Kasten's own

## Behind a proxy

`setup` copies `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY` and `NODE_EXTRA_CA_CERTS` from its own
environment into the `env` block of `~/.claude/settings.json`, and removes those its
environment no longer has. Claude Code then has the proxy also when it starts without a
shell — as the Claude desktop app starts it in WSL. Whatever sets these variables for the
machine's shells stays their only source; run `setup` again after it changed them.

On a new machine, Claude Code started by the desktop app has no proxy until `setup` ran.
Run the first `setup` from a Claude Code session started in a shell on that machine, not
from the desktop app.

## Changing asf/

Any Kasten can be the origin of a change to `asf/`: it is made and tried in the Kasten that
needs it, and the template, a clone of
[zettelkasten-template](https://github.com/xxthunder/zettelkasten-template), carries it to the
others. Each Kasten records in `.asf-base` the template commit its `asf/` last matched.

1. **Take in first**: `git pull` in the template clone, then
   `python3 asf/scripts/kasten.py update <kasten>` there. It merges the template's changes
   since the base into the Kasten's `asf/`, keeps the Kasten's own, and records the new base.
   Where both sides changed the same lines it leaves conflict markers and commits nothing.
2. **Hand on**: from the Kasten,
   `python3 asf/scripts/kasten.py export <clone> --patterns scripts/leak-patterns.txt`. It
   refuses while the clone is not on the base, and stops when a pattern from the Kasten's own
   `scripts/leak-patterns.txt` matches. Review, commit and push in the clone.
3. **Everywhere else**: `update`, as in step 1.
