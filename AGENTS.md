# AGENTS.md — the Kasten template

This repository is a clone of the template a Zettelkasten is made from. It stays a clean
clone: never edit, commit or push here. Two things are done from here.

## "Make me a new Zettelkasten"

1. **Ask**, one question at a time:
   - where the Kasten goes — suggest `~/dev/<org>/<name>` after the remote's path, or
     `~/dev/zettelkasten` without a remote;
   - the clone URL of the new, empty repository it is pushed to — optional, it can be added
     later;
   - the language of its notes, hubs, backlog and of the conversation — English unless the
     author says otherwise.
2. **Check the git identity**: `git config --global user.name` and `user.email` must be set.
   If not, ask the author to set them — identity is never guessed or filled in.
3. **Make it**: `python3 asf/scripts/kasten.py new <path> --remote <url>` (without
   `--remote` when there is none). It copies `asf/` and the starting files, commits on
   `develop`, and sets this machine up: `~/.claude/CLAUDE.md`, the plugins,
   `~/.claude/settings.json`, the hook, the git workflow settings, the zsh fragment.
4. **Language**: if it is not English, change the language line in the new Kasten's
   `CONVENTIONS.md` → Language and the section *Conversation language* in its `AGENTS.md`,
   and commit that in the new Kasten.
5. **Old global instructions**: when `kasten.py` says it kept an old `~/.claude/CLAUDE.md`,
   show the author what it says and offer to move what still applies into the new Kasten's
   `claude/CLAUDE.md`; commit that in the new Kasten.
6. **Push**, when there is a remote: `git -C <path> push -u origin develop`.
7. **Tell the author** to restart Claude Code and to start sessions in the new Kasten from
   now on. Name every other backup `kasten.py` reported, and every plugin it could not
   install — usually git cannot reach GitHub, behind a proxy for instance; once it can,
   `python3 asf/scripts/kasten.py setup` in the new Kasten installs them.

## "Update my Zettelkasten"

1. `git pull` here.
2. `python3 asf/scripts/kasten.py update <kasten>` — it refuses a Kasten with uncommitted
   changes; then ask the author to commit or stash first.
3. Show the commit it made (`git -C <kasten> show --stat`), and push it after the author
   agrees.
