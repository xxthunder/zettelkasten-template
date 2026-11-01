/*
 * The Agentic Software Forge (ASF): how one backlog item runs through the closed loop,
 * from its card on the board to an evidence package the author confirms.
 *
 * Generic on purpose: this file belongs to the template, so it names roles
 * ("target repository"), not one Kasten's repositories. Elements tagged "Planned"
 * do not exist yet; the backlog item that builds them is named in their description.
 *
 * Validated by asf/scripts/lint.sh. Render it with Structurizr, e.g.
 *   docker run --rm -p 8080:8080 -v "$PWD/asf/architecture:/usr/local/structurizr" structurizr/structurizr local
 */
workspace "Agentic Software Forge" "The closed engineering loop, with the Kasten as its root." {

    !identifiers hierarchical

    model {
        author = person "Author" "Ranks the work, pulls an item, confirms the evidence package, merges."

        asf = softwareSystem "Agentic Software Forge" "The author's way of building software with AI agents: the same workflow on every machine." {
            kasten = container "Kasten" "Knowledge repository and root of the work: contracts, board, log, learnings." "Git repository" "Repository" {
                contracts = component "Contracts" "asf/AGENTS.md: Board, Logbook, Learnings and Closed loop — gate, rubric and the sections of the evidence package." "Markdown"
                board = component "Board" "engineering/board.md: Next and In Progress across all repositories." "Markdown"
                logbook = component "Logbook" "engineering/log.md: started, note, done — one line per event." "Markdown"
                generalRubric = component "General rubric" "asf/rubric.md: what a reviewer judges in every repository — prior art first, mechanical work is code, rules say what to do, simplicity, test first, the record stays true, nothing private leaves its place." "Markdown"
                registry = component "Repository registry" "engineering/repos.md: repository name → remote, ID prefix." "Markdown"
            }

            session = container "Claude Code session" "The controller: works one item through the loop in the target repository's worktree." "Claude Code" "Agent"

            devSkills = container "xxthunder-dev-skills" "The plugin that works the Kasten structure and the backlogs." "Claude Code plugin" "Plugin" {
                backlogOps = component "backlog-ops" "Pulls, ticks and closes an item; moves its card." "Skill"
                next = component "next" "Shows the board; puts and drops cards." "Skill"
                logbookSkill = component "logbook" "Writes started, note and done lines." "Skill"
                refinement = component "refinement" "Creates items through backlog.py new." "Skill"
                loopDriver = component "Loop driver" "Reads the target repository's gate and rubric, hands the rubric to the reviewers, ends the loop on a green gate, writes the evidence package (XAS-055)." "Skill" "Planned"
                backlogScript = component "backlog.py" "Every mechanical backlog step: new, set-status, toc, show, check." "Python"
                storeScript = component "store" "Resolves a store, reads a contract, commits and pushes one file." "Shell"
            }

            implementer = container "Implementer subagent" "Writes the test, then the code, for one task; commits." "general-purpose subagent, superpowers prompt" "Agent"
            taskReviewer = container "Task reviewer subagent" "Reads one task's diff against the task and the target repository's rubric; reports findings." "general-purpose subagent, superpowers prompt" "Agent"
            finalReviewer = container "Final reviewer subagent" "Reads the whole branch once all tasks are done." "general-purpose subagent, superpowers prompt" "Agent"
        }

        superpowers = softwareSystem "superpowers" "Third-party plugin: writing-plans, subagent-driven-development, finishing-a-development-branch, and the prompt templates for implementer and reviewers. Adopted, not rebuilt (ADR-0013 of xxthunder-agentic-skills)." "External"

        target = softwareSystem "Target repository" "Any repository on the board. Supplies its own gate and rubric, in the form the Closed loop contract sets." "Repository" {
            agentsMd = container "AGENTS.md" "The repository's rules; its section Closed loop names the gate, the rubric and where the gate runs." "Markdown"
            backlog = container "Backlog" "docs/backlog/: one file per item; the item is the design document of its change." "Markdown"
            worktree = container "Feature worktree" "A feature branch in its own worktree, one per item." "Git worktree"
            gate = container "Gate" "scripts/gate: one executable that runs every deterministic check — tests, lint, Molecule, behavioural evals — and exits 0 only when all are green. The author and CI call it too." "Script"
            rubric = container "Rubric" "docs/rubric.md: what the reviewers judge in this repository's changes — only what needs judgment." "Markdown" "Planned"
        }

        forge = softwareSystem "Forge" "GitHub or Gitea: the pull request carries the evidence package; CI runs the gate again." "External"

        # Context
        author -> asf "Pulls items, confirms evidence"
        author -> forge "Reads the evidence package, merges"
        asf -> target "Changes, through a feature branch"
        asf -> superpowers "Runs the loop with"
        asf -> forge "Opens the pull request with the evidence package"

        # The author and the board
        author -> asf.kasten.board "Ranks the cards" "next put"
        author -> asf.session "Pulls an item, answers questions" "chat"

        # The session uses both plugins
        asf.session -> asf.devSkills "Invokes skills"
        asf.session -> superpowers "Plans the item, runs subagent-driven-development"

        # Mechanics through scripts
        asf.devSkills.backlogOps -> asf.devSkills.backlogScript "Sets the status"
        asf.devSkills.refinement -> asf.devSkills.backlogScript "Creates the item"
        asf.devSkills.backlogScript -> target.backlog "Reads and writes items"
        asf.devSkills.backlogOps -> asf.devSkills.storeScript "Moves the card"
        asf.devSkills.next -> asf.devSkills.storeScript "Puts and drops cards"
        asf.devSkills.logbookSkill -> asf.devSkills.storeScript "Writes a log line"
        asf.devSkills.storeScript -> asf.kasten.contracts "Reads a contract"
        asf.devSkills.storeScript -> asf.kasten.board "Commits the board"
        asf.devSkills.storeScript -> asf.kasten.logbook "Commits the log"
        asf.devSkills.next -> asf.kasten.registry "Resolves a repository"

        # The loop
        asf.devSkills.loopDriver -> asf.kasten.contracts "Reads the Closed loop contract"
        asf.devSkills.loopDriver -> target.agentsMd "Reads where the gate and the rubric are"
        asf.devSkills.loopDriver -> asf.kasten.generalRubric "Hands it to the reviewers as global constraints"
        asf.devSkills.loopDriver -> target.rubric "Hands it to the reviewers as global constraints"
        asf.devSkills.loopDriver -> target.gate "Runs it; the loop ends only when it is green"
        asf.devSkills.loopDriver -> forge "Writes the evidence package into the pull request"
        asf.session -> asf.implementer "Dispatches, one task at a time"
        asf.session -> asf.taskReviewer "Dispatches after each task, with the rubric"
        asf.session -> asf.finalReviewer "Dispatches once, for the whole branch"
        asf.implementer -> target.worktree "Commits, test first"
        asf.implementer -> target.gate "Runs the tests of its task"
        asf.taskReviewer -> target.rubric "Judges the diff against"
        asf.taskReviewer -> asf.kasten.generalRubric "Judges the diff against"
        asf.taskReviewer -> target.worktree "Reads the diff"
        asf.finalReviewer -> target.worktree "Reads the branch"
        asf.session -> target.gate "Runs before the loop ends"
        asf.session -> forge "Opens the pull request"
        target.worktree -> forge "Pushed to"
    }

    views {
        systemContext asf "Context" "Who and what the Agentic Software Forge works with." {
            include *
            autoLayout lr
        }

        container asf "Containers" "The parts of the forge and the target repository they change." {
            include *
            autoLayout lr
        }

        container target "TargetRepository" "What a repository supplies to the loop, and who uses it." {
            include *
            autoLayout lr
        }

        component asf.devSkills "Plugin" "The skills of xxthunder-dev-skills and the scripts that do their mechanical steps." {
            include *
            autoLayout lr
        }

        dynamic asf "Loop" "One item, from its card to the merge." {
            author -> asf.session "Pulls the item from the board"
            asf.session -> asf.devSkills "backlog-ops: In Progress, card to In Progress, log line"
            asf.session -> superpowers "writing-plans: the item becomes a plan of tasks"
            asf.session -> asf.implementer "Task n: write the test, then the code"
            asf.implementer -> target.worktree "Commits the task"
            asf.session -> asf.taskReviewer "Review task n against the task and the rubric"
            asf.taskReviewer -> asf.kasten "Judges the diff against the general rubric"
            asf.taskReviewer -> target.rubric "Judges the diff against the repository's rubric"
            asf.session -> asf.implementer "Fix round, until approved (at most five)"
            asf.session -> asf.finalReviewer "Review the whole branch"
            asf.session -> target.gate "Run scripts/gate; a red gate sends the work back into a fix round"
            asf.session -> forge "Open the pull request with the evidence package"
            author -> forge "Confirms the evidence, merges"
            autoLayout lr
        }

        styles {
            element "Person" {
                shape Person
                background #1f4e79
                color #ffffff
            }
            element "Software System" {
                background #2e75b6
                color #ffffff
            }
            element "Container" {
                background #5b9bd5
                color #ffffff
            }
            element "Component" {
                background #9dc3e6
                color #000000
            }
            element "External" {
                background #7f7f7f
                color #ffffff
            }
            element "Agent" {
                shape Robot
            }
            element "Repository" {
                shape Folder
            }
            element "Plugin" {
                shape Component
            }
            element "Planned" {
                border dashed
                opacity 60
            }
        }
    }
}
