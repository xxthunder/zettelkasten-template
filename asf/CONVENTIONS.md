# Zettelkasten Conventions — the Agentic Software Forge part

The rules every Kasten made from the template shares. The Kasten's own `CONVENTIONS.md` in its
root adds its areas and the language of its notes. This file belongs to the template; an
update replaces it.
**Claude Code: always read this file and the Kasten's own one before editing notes.**

## Principles

1. **Atomic learnings**: each learning captures exactly one claim, worded in the author's own
   words — the title is the claim, not the topic.
2. **Connection over collection**: the value lies in the links between notes, not in their
   number.
3. **Own thinking first**: the agent helps with review, structure and connections — but the
   claim of a learning and its wording come from the author.

**The gate for learnings** — all three tests must hold, or it is not a learning:

1. Does it stay true when the project is deleted? *(transferable)*
2. Would it have made an earlier session go differently? *(useful)*
3. Can the author say it now, in their own words? *(owned)*

If **only** test 3 fails, the candidate goes to `inbox/` — "not yet in my own words" — and
`process-inbox` promotes it once the wording is there. `inbox/` is the exit for exactly this
one case, not the default path; a candidate arriving there is a signal. Most corrections fail
test 2 — a full working day yields two candidates rather than twenty, and that rate is the
goal.

## Folder structure

One top-level folder per content type. Every Kasten has these:

```
asf/          — the template's part: these conventions, the agent contracts, templates,
                scripts; replaced as a whole by an update
inbox/        — raw captures, fleeting notes; learning candidates not yet in own words
learnings/    — learnings: insights that outlive a project — the core of the system
literature/   — literature notes (summaries of sources)
engineering/  — tinkering: house, network, tools, agent stack; with log.md, the chronicle
                across all repos, repos.md, the registry of repos the Kasten points into,
                and next.md, the ranked list across all repos
docs/         — meta: backlog, decisions
memory/       — the agent's auto-memory: the agent writes it itself; not an area, no
                learnings
```

A Kasten adds its own areas in its own `CONVENTIONS.md`. No catch-all `projects/`. Every
content area has a `README.md` as its hub (see Linking).

## File names

- **Learnings**: `YYYYMMDDHHMMSS-slug.md`, English slug (e.g.
  `20260910204101-a-negative-finding-is-only-as-good-as-its-boundary.md`) — the timestamp is
  the stable ID that survives a later change of title
- **Literature notes**: `lit-AUTHOR-YEAR-slug.md` (e.g.
  `lit-ahrens-2017-how-to-take-smart-notes.md`)
- **Engineering notes**: `slug.md` in `engineering/`
- **Inbox notes**: any name; renamed or deleted when processed
- **Area hub**: `README.md` in its area (no `index.md`)

## Frontmatter

**Every note** uses YAML frontmatter. The required core for **all** types:

```yaml
---
title: "Title of the note"
created: 2025-02-22T14:30:00
tags: [tag1, tag2]
type: learning | literature | engineering | <a type of the Kasten's own areas>
---
```

One `type` value per top-level area; a Kasten's own areas add theirs. Inbox notes carry no
`type` yet — it is set when the note is processed.

Optional fields for every type:

```yaml
updated: 2025-02-22T14:30:00   # when the note was edited later
source: ""                      # the source; REQUIRED for type: literature
                                # when set, also link it in the text (see Linking)
related: []                     # list of related file names (without path)
```

## Linking

- **Relative Markdown links** everywhere: within a folder `[file-name](file-name.md)`, across
  folders `[file-name](../area/file-name.md)`. The link text is the file name without `.md`
  by default; free text is fine where it helps the sentence. Links like this work in
  Obsidian and in a forge's web view
- **Moves**: move notes in Obsidian — it updates the links. Whoever moves outside it
  (`git mv`) updates the links themselves; `asf/scripts/lint.sh` reports dead links and
  every wiki-link
- **Plain Markdown**: no Obsidian-specific syntax in notes — no callouts, embeds (`![[…]]`)
  or Dataview blocks
- Prefer explicit context: `As [note](note.md) describes, the insight is…` rather than just
  `See [note](note.md)`
- Navigation within an area goes through its `README.md` hub (no separate index note)
- Hub back-link from a note as `[← Area name](README.md)` — here the link text is the area's
  name, not the file name
- **Direction rule**: the Kasten points into repos — item IDs, paths, URLs. **No repo points
  into the Kasten**: no `CLAUDE.md`, no skill text, no item in another repo names it, its path
  or its remote. What knows the Kasten is the machine — the user configuration of the skills
  `learnings`, `logbook` and `next` (`LEARNINGS_*`, `LOGBOOK_*`), never a repo
- **Link sources visibly**: when `source:` is set, the source must also appear as a clickable
  link in the body of the note — frontmatter alone is not enough, because it is hidden as a
  property block when reading. Prefer inline with context over a trailing list of links.
  When a source file (e.g. from `inbox/`) contains links, each of them belongs in the target
  note — links are content, not decoration, and must not get lost in processing.

## Tags

- Lowercase, hyphenated: `#systems-thinking`, `#networking`
- Keep the tag vocabulary small and deliberate — check existing tags before creating new ones
- Tags describe *topics*, links describe *relationships*

## Engineering Log

`engineering/log.md` is the chronicle: one line per *event*, across all repos, English. The
hub is the map — one line per *note*, overwritten; the log is the diary — only added to. The
binding format is the `Logbook` contract in [AGENTS.md](AGENTS.md); in short:

- **Three line types**: `started`, `note`, `done`. No fourth until one is needed.
- **Address**: `<repo> <ITEM-ID>`; the IDs are unique per repo. Repos without a backlog:
  `<repo> #123`. The short name `<repo>` comes from the registry `engineering/repos.md` —
  four columns: **Repo** (short name, linked to the web URL) · **Remote** (clone URL) ·
  **IDs** (prefix of the backlog, `#` without one) · **What it is** (one sentence; what the
  repo *is* stands in its README). English, one line per repo, curated — no script derives
  it.
- **Newest on top**, **append-only**, **one commit per line, pushed at once** — in an
  ephemeral container an unpushed line is not a line.
- **Reach**: repo work from any repo, and tinkering. A Kasten's own areas with dated hubs are
  their own chronicle.
- **Who writes**: the author or the `logbook` skill. No back-filling of old work.

## Language

By text type, not by folder. This file fixes what is English in every Kasten:

| Text type | Language |
|---|---|
| Everything in `asf/` — the template | English |
| Learnings (`learnings/`) | English |
| Engineering log (`engineering/log.md`) | English |
| Repo registry (`engineering/repos.md`) | English — its subject is repos and IDs, its readers are log and learnings |
| Ranked list (`engineering/next.md`) | English — a skill reads and writes it, like the log |
| The agent's auto-memory (`memory/`) | English |
| Code — scripts, tests, identifiers, comments, output | English, always — whatever the language of the conversation and the surrounding notes |

**Everything else** — area notes, hubs, `docs/`, and the conversation with the agent — is in
the language the Kasten picks in its own `CONVENTIONS.md`. The language of the conversation
is not the language of the artifact. A folder may hold text types of both languages.

## Claude Code Guidelines

- **Process the inbox**: turn fleeting notes into fitting notes (learning, literature or
  area), but always have them confirmed first
- **Find connections**: search across all notes and suggest missing links
- **Challenge ideas**: act as a sparring partner — ask questions, point out gaps
- **Never create learnings automatically** without the author's consent — the author words
  the claim
- **Follow the conventions**: naming, frontmatter and linking exactly
- **Design goes into the backlog item, an area note only on request**: the item lives in the
  backlog of the repo where the work happens — in the Kasten only for work without a repo or
  without a backlog, and as the central item for work across several repos. Findings,
  design, sources and open questions stand in the item; an area note is written only when
  the author asks for it
- **Suggest, don't decide**: suggest tags and links, let the author choose
- **Lint and validation**: on request, check broken links, orphaned notes and inconsistent
  tags
