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
                registry = component "Repository registry" "engineering/repos.md: repository name → remote, ID prefix; a gate the author corrects." "Markdown"
            }

            session = container "Claude Code session" "The controller: works one item through the loop in the target repository's worktree." "Claude Code" "Agent"

            devSkills = container "xxthunder-dev-skills" "The plugin that works the Kasten structure and the backlogs." "Claude Code plugin" "Plugin" {
                backlogOps = component "backlog-ops" "Pulls, ticks and closes an item; moves its card." "Skill"
                next = component "next" "Shows the board; puts and drops cards." "Skill"
                logbookSkill = component "logbook" "Writes started, note and done lines." "Skill"
                refinement = component "refinement" "Creates items through backlog.py new." "Skill"
                loopDriver = component "Loop driver" "Finds the target repository's gate — named by it, corrected in the registry, or derived from its CI — and its rubric, hands the rubric to the reviewers, ends the loop on a green gate, writes the evidence package (XAS-055)." "Skill" "Planned"
                backlogScript = component "backlog.py" "Every mechanical backlog step: new, set-status, toc, show, check." "Python"
                storeScript = component "store" "Resolves a store, reads a contract, commits and pushes one file." "Shell"
            }

            implementer = container "Implementer subagent" "Writes the test, then the code, for one task; commits." "general-purpose subagent, superpowers prompt" "Agent"
            taskReviewer = container "Task reviewer subagent" "Reads one task's diff against the task and the target repository's rubric; reports findings." "general-purpose subagent, superpowers prompt" "Agent"
            finalReviewer = container "Final reviewer subagent" "Reads the whole branch once all tasks are done." "general-purpose subagent, superpowers prompt" "Agent"
        }

        superpowers = softwareSystem "superpowers" "Third-party plugin: writing-plans, subagent-driven-development, finishing-a-development-branch, and the prompt templates for implementer and reviewers. Adopted, not rebuilt (ADR-0013 of xxthunder-agentic-skills)." "External"

        target = softwareSystem "Target repository" "Any repository on the board, the author's or someone else's. Its gate is the one it names or the one its CI implies." "Repository" {
            agentsMd = container "AGENTS.md" "The repository's rules; an optional section Closed loop names the gate, the rubric and where the gate runs." "Markdown"
            backlog = container "Backlog" "docs/backlog/: one file per item; the item is the design document of its change." "Markdown"
            worktree = container "Feature worktree" "A feature branch in its own worktree, one per item." "Git worktree"
            ci = container "CI definition" "pypeline.yaml, .github/workflows/, .gitea/workflows/ or a Jenkinsfile: the checks a pull request must pass." "YAML, Groovy"
            gate = container "Gate" "The command that runs every deterministic check — tests, lint, Molecule, behavioural evals — and exits 0 only when all are green: the one the repository names, often scripts/gate, or the one derived from its CI." "Command"
            rubric = container "Rubric" "docs/rubric.md, else CONTRIBUTING.md: what the reviewers judge in this repository's changes — only what needs judgment." "Markdown" "Planned"
        }

        forge = softwareSystem "Forge" "GitHub, Gitea or Jenkins: the pull request carries the evidence package; CI runs the checks again, and is the gate where they cannot run locally." "External"

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
        asf.devSkills.loopDriver -> asf.kasten.registry "Reads a gate correction"
        asf.devSkills.loopDriver -> target.ci "Derives the gate from, when the repository names none"
        asf.devSkills.loopDriver -> asf.kasten.generalRubric "Hands it to the reviewers as global constraints"
        asf.devSkills.loopDriver -> target.rubric "Hands it to the reviewers as global constraints"
        asf.devSkills.loopDriver -> target.gate "Runs it; the loop ends only when it is green"
        asf.devSkills.loopDriver -> forge "Waits for green CI checks, where the CI is the gate"
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
            asf.session -> target.gate "Run the gate — or wait for the CI where it is the gate; a red gate sends the work back into a fix round"
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
