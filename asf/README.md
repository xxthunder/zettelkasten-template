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

## What lives here

`asf/` is the template's part of a Kasten. An update replaces this folder as a whole; a Kasten
changes its own files in its root instead — its own `AGENTS.md` imports
[AGENTS.md](AGENTS.md) from here, its own `CONVENTIONS.md` adds to
[CONVENTIONS.md](CONVENTIONS.md).

- [AGENTS.md](AGENTS.md) — the agent's roles and the contracts for learnings, log and the
  board
- [CONVENTIONS.md](CONVENTIONS.md) — principles, file names, frontmatter, linking, language
- `templates/` — a template per note type: `learning`, `literature`, `engineering`
- `scripts/` — `lint.sh`, `review.sh`, `new-zettel.sh`, and `kasten.py`, which makes a new
  Kasten (`new`), sets a machine up for one (`setup`) and updates one (`update`); its tests
  are in `tests/` (`cd asf && uv run --group dev pytest`)
- `claude/` — the global instructions, the shared part of the user settings (plugins,
  marketplaces, hook, deny rules) and the hook itself; `setup` points `~/.claude` at them
  and installs the plugins
- `shell/asf.zsh` — `PATH` for `claude` and `uv`, and `claude-tmux`; `setup` sources it from
  `~/.zshrc`
- `skills/` — the Kasten's own skills (`process-inbox`); `setup` links them into
  `.claude/skills/`
- `seed/` — the files a new Kasten starts with; afterwards they are the Kasten's own
