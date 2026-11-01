# Rubric — what a reviewer judges in every repository

The general part of the rubric for the closed loop (contract `Closed loop` in
[AGENTS.md](AGENTS.md)). The reviewers get this file and the target repository's own
`docs/rubric.md`, both as binding constraints of the plan.

Only what needs judgment is here. Whatever a script, a test or the gate decides is checked
there, not by a reviewer. The reviewer prompt of `superpowers:subagent-driven-development`
already judges spec compliance and code quality — clean separation, error handling, edge
cases, tests that verify real behaviour; that is not repeated here either.

Answer each criterion with evidence from the diff: a `file:line` and what it shows. A
criterion that does not apply to the change is answered "not applicable" with the reason.

## 1. Prior art first

Does the change build something that an installed plugin, the platform, a library or a
well-known tool already does? If it builds its own anyway, does the item or an ADR name the
existing thing and the gap it leaves? A finding is a new mechanism with no such reason.

## 2. Mechanical work is code

Does the change ask an agent or a person to perform by hand a step a script could perform —
allocating an ID, editing a generated table, computing a date, inserting a line at the right
place, running a sequence of commands? A finding is a deterministic step written as prose
instructions.

## 3. Rules say what to do

Does every new or changed rule for an agent — in `AGENTS.md`, `CLAUDE.md`, a skill, a prompt,
a memory — state the action to take? A prohibition comes second, after the positive rule,
and only where one is needed. A finding is a rule that only forbids.

## 4. The simplest thing that serves the item

Does the change build only what its item asks for (KISS, YAGNI)? Does it keep one source of
truth, deriving rather than copying (DRY)? A finding is an option, an abstraction or a
configuration point no current need asks for, or a fact now stated in two places.

## 5. The test came first and would fail without the change

Does every behaviour the change adds or alters have a test that fails without the change?
Is there evidence it was written first — the implementer's report, or the test in an
earlier commit than the code? A finding is new behaviour with no test, or a test that
would pass on the old code.

## 6. The record stays true

Does the change keep the repository's record true: the item's acceptance criteria and scope
decisions match what was built, a decision that outlives the change and passes the
three-part test has an ADR, and the architecture model and documents still describe the
code? A finding is a design choice that lives only in the diff or the conversation.

## 7. Nothing private leaves its place

Does anything in the change reach a repository it does not belong in — credentials, host
names and addresses of a private network, the names of family members, the content of a
private Kasten in a public repository? A finding is any such line in a repository whose
readers should not see it.
