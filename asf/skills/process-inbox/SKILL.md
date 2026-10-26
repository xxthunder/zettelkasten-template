---
name: process-inbox
description: Turns notes from inbox/ into learnings, literature or area notes following the Kasten's conventions. TRIGGER on "process inbox", "/process-inbox", or when the author asks to process fleeting notes — in any language.
---

# Process the inbox

You are the Inbox Processor from `asf/AGENTS.md`. Goal: turn fleeting captures in `inbox/`
into structured notes — **with confirmation**, never automatically.

## Preparation (once per run)

1. Read `asf/CONVENTIONS.md`, `CONVENTIONS.md` and `AGENTS.md` if they are not in context yet.
2. List `inbox/`. If it is empty → say so and stop.
3. Look at the existing tag vocabulary and the area hubs, so suggestions fit what is there:
   - every area's `README.md` (the areas are listed in `CONVENTIONS.md` and
     `asf/CONVENTIONS.md`)
   - `learnings/` (skim tags and titles)

## Per note

1. **Read.** Read the whole file.
2. **Find the core idea.** One note = one idea. Several ideas: suggest a split.
3. **Decide the target** (with a reason):
   - `learnings/` — stays true when the project is gone; useful; can be put in own words
     (the three tests in `asf/CONVENTIONS.md`); English
   - `literature/` — summary of a source (book, article, paper)
   - `engineering/` — tinkering: house, network, tools, agent stack
   - one of the Kasten's own areas (`CONVENTIONS.md` → its areas)
   - **Delete** — when there is no substance (and why)
4. **Make a proposal**: title, file name (by convention), target folder, draft frontmatter,
   2–4 suggested links (relative Markdown links, see Linking in `asf/CONVENTIONS.md`) with a
   reason each, tag suggestions (chosen from existing tags, new ones marked).
5. **Wait for confirmation.** Exception: the author explicitly says to go ahead with all of
   them (`AGENTS.md` may name the phrase).
6. **Carry it out** after approval:
   - Create the new file in the target folder, following the conventions of that area in
     `asf/CONVENTIONS.md`, `CONVENTIONS.md` and `AGENTS.md` exactly (file name, frontmatter,
     the area's template).
   - **Keep every link of the source file**: before deleting the inbox file, check each URL
     in it against the target note. External sources go into `source:` **and** visibly into
     the text (see Linking in `asf/CONVENTIONS.md`) — a link only in the frontmatter is
     invisible when reading and does not count as kept.
   - For an area note: update the area's hub `README.md` (new entry on top).
   - For a learning or literature note: add links in linked notes where the author agrees;
     for a learning, add the hub line in `learnings/README.md` (newest on top).
   - Delete the inbox file (`git rm` if it is tracked already).

## File names (quick reference)

- learning: `YYYYMMDDHHMMSS-slug.md` (timestamp = now, English slug)
- literature: `lit-AUTHOR-YEAR-slug.md`
- engineering and the Kasten's own areas: as `CONVENTIONS.md` and `asf/CONVENTIONS.md` say

## At the end

- Summary: processed / moved / deleted / open.
- Do **not** commit automatically — offer it, with a commit message in the style of the
  existing commits.

## Rules of conduct

- Answer in the conversation language the Kasten's `AGENTS.md` names.
- Stay brief — one compact proposal block per note, no essays.
- Never decide silently: tags, links and splits are suggestions, the author chooses.
- Invent no frontmatter fields that the conventions do not name.
- When unsure about the target (e.g. "learning or area note?"), ask instead of guessing.
