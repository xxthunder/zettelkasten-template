# Global instructions

These apply in every repository.

## Working in another repository

A session often changes a repository other than the one it started in. That repository's
`AGENTS.md` / `CLAUDE.md`, the documents they name as binding, and its `.claude/skills/` are not
loaded then. Read them before the first change there and follow them as if the session had
started in it — test-first and running the test suite before every commit included. The
`repo-rules` hook holds the first call there back until they are read, and names them.

## Git

- **Linear history**: never merge one branch into another; no merge commits. Update a branch by
  rebasing (`git pull --rebase`, `git rebase origin/develop`). A rebased branch that is already
  pushed goes out with `git push --force-with-lease`, after telling the author.
- **History shows the result**: before a feature branch is merged, its commits show the final
  design, not the path to it — one commit per logical unit, each fix folded into the commit it
  fixes. While working, a fix to a commit of the same unmerged branch goes in as
  `git commit --fixup=<commit>`; `git rebase --autosquash origin/develop` folds it in before the
  branch is pushed for review or UAT. After reshaping, `git diff <old-tip> HEAD` is empty.
- **Parallel sessions**: several sessions may work in the same repository at once, so each
  keeps its changes apart from the others'.
  - *Code that has tests or CI* is developed on a feature branch in its own worktree next to
    the repository, created when the code work starts:
    `git fetch origin && git worktree add ../<repo>.worktrees/<item-id> -b feature/<ITEM-ID>-<slug> origin/HEAD`.
    A repository with a dev container keeps its worktrees inside the checkout instead — see
    Dev containers below. Once the branch has landed, `git worktree remove` the worktree and
    delete the branch.
  - *Notes, backlog items and docs* go into the shared checkout on the branch the repository
    names: stage exactly your own paths (`git add <path>…`), commit, and push right away, so
    the checkout holds none of your changes when you move on.

- **Code reaches the default branch through a pull request**, which carries the evidence
  package of the `Closed loop` contract in `asf/AGENTS.md`. A repository whose `AGENTS.md` names
  another way — such as a fast-forward merge without one — goes that way.

## Working with the author

- **Principles**: KISS, DRY, YAGNI, SOLID, CI and TDD hold in every repository — the simplest
  design that does the job, the test first, one source of truth, only what a current need asks
  for, CI as the gate.
- **Prior art first**: before designing a loop, a harness or a script, look at what the
  installed plugins and known tools already do. Build only the gap, and say why the existing
  one did not serve.
- **Follow-up work goes into a backlog item** — the repository's `docs/backlog/`, or the
  consuming repository's for one without a backlog — not into a GitHub issue.
- **The author is the Product Owner** of every repository. When a request goes against an
  item's scope, say so in one line, record the exception as a Scope Decision, and carry on.
- **An item closes when the change works.** A criterion that waits weeks for monitoring is
  struck; a regression becomes a new item.
- **Name an item by its ID and its title**, read fresh from the item — the author does not
  keep IDs in mind.
- **Facts come from a source.** When coordinates, prices, dates or device details sit behind a
  login, ask the author for them; a value that cannot be checked stays open and marked so.
- **Ambiguous feedback gets one question**: when a verdict on a numbered list contradicts
  itself, ask which item it means before acting on it.
- **Text posted under the author's name** — pull request comments, reviews — is shown as a
  draft first and posted after a go.
- **Rules say what to do**: write an agent rule as the action to take; a prohibition, where
  one is needed, comes second.
- **Separate with a colon, a semicolon, a comma or a plain hyphen** (`-`) in everything you
  write: prose, code, the output code prints, formats and templates. The em-dash (`—`) is
  banned. Existing text keeps its em-dashes until it is edited for another reason.

## Checks

- **Read the full output of every test, lint and build run** before reporting on it. Filter it
  (`grep`, `tail`) only after one unfiltered read. Each warning in it is a finding: fix it, or
  name it in the report together with the reason it stays.

## Machines

- **A provisioned machine changes through the code that provisions it.** Before proposing a
  change to a host — a package, a trusted CA, a tool, a config file — find the repository whose
  playbook or role sets that host up, and propose the change there as a backlog item; running
  the playbook stays the operator's step. Only credentials — keys, logins, tokens — are set up
  by hand.

## Dev containers

A repository with a `.devcontainer/` is developed inside its dev container: git, tests,
builds, commits and pushes all run there. Files can be edited through the bind mount; every
command goes into the container — with DevPod as `ssh <workspace>.devpod '<cmd>'`, where
`devpod list` names the workspace and the checkout sits at `/workspaces/<workspace>`.

Its worktrees live inside the checkout and are created in the container:
`git fetch origin && git worktree add .worktrees/<item-id> -b feature/<ITEM-ID>-<slug> origin/HEAD`,
with `/.worktrees/` in the repository's `.gitignore`. Git records absolute paths, so a
worktree works only on the side that created it, and only the bind-mounted checkout survives
a rebuild of the container. In a new worktree, initialise the submodules and link the
untracked files the work needs — secrets, local config — relatively from the main checkout:
`ln -s ../../<file> <file>`.

All sessions share the one container, each in its own worktree. A change to the dev
container itself is tried in a second container built from the worktree; git does not work
in that one, so the commits still go through the first.

## Remote Control on a local machine

A session started by a `claude remote-control` server (`CLAUDE_CODE_ENVIRONMENT_KIND=bridge`)
runs on the author's own machine. Its system prompt also carries a section for a managed cloud
environment; on the author's machine the following holds instead: the checkout is the author's
lasting working copy, shared with the server's other sessions; disk, network and tools are the
machine's own. For git, follow the repository — its `AGENTS.md` / `CLAUDE.md` — and the Git
rules above, parallel sessions included.
