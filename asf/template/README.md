# zettelkasten-template

The template for a Zettelkasten worked on with Claude Code — the how of the
[Agentic Software Forge](asf/README.md): the structure of a Kasten, the contracts the agent
skills work by, the global rules and settings of the agent, and a tested script that sets a
machine up for it. What goes into a Kasten made from it — notes, learnings, log lines,
remotes, names — is never in here.

## Start a Kasten

1. Install [Claude Code](https://docs.claude.com/en/docs/claude-code), `git` and `python3`;
   set your git identity (`git config --global user.name …`, `user.email …`).
2. Clone this template and start Claude Code in the clone:

   ```bash
   git clone https://github.com/xxthunder/zettelkasten-template.git ~/dev/xxthunder/zettelkasten-template
   cd ~/dev/xxthunder/zettelkasten-template && claude
   ```

3. Say: *"Make me a new Zettelkasten from this template."* Claude asks where it should go,
   for the remote of your new repository and for the language of your notes, then runs
   `asf/scripts/kasten.py new` — see [AGENTS.md](AGENTS.md).
4. Restart Claude Code and work from the new Kasten.

The clone is how updates arrive, and how a Kasten's own changes reach the others (see
Changing the template). The new Kasten is a repository of its own, with a history of its own.

## Update a Kasten

`git pull` in the clone, then tell Claude *"Update my Zettelkasten from this template."* It
runs `asf/scripts/kasten.py update <kasten>`, which merges the template's changes into the
Kasten's `asf/`, keeps the Kasten's own changes there, and commits. Everything outside `asf/`
is the Kasten's own and is never touched.

## Changing the template

Changes come from the Kastens: any Kasten changes its `asf/`, tries the change, takes in the
template with `update` and hands its change on with `kasten.py export`. The export stops when a
pattern from the Kasten's own `scripts/leak-patterns.txt` matches — fill it with your hosts,
remotes and names before the first export. See `asf/README.md` → Changing asf/.

## License

[MIT](LICENSE)
