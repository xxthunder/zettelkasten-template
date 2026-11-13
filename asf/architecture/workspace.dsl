/*
 * The Agentic Software Forge (ASF): one OS instance with everything on it, and how one
 * backlog item runs through the closed loop on it, from the author's request to the merge.
 * Cut after C4: the context, the containers of the instance, the components of the
 * Coding Agent, the Harness and the Kasten, and two dynamic views, Loop and Unit.
 *
 * Generic on purpose: this file belongs to the template, so it names roles
 * ("Repository checkout"), not one Kasten's repositories or hosts. Every element exists
 * today: the model shows the closed loop as the shipped closed-loop skill runs it, not a
 * plan, so no element is tagged "Planned".
 *
 * Validated by asf/scripts/lint.sh. Render it with Structurizr, e.g.
 *   docker run --rm -p 8080:8080 -v "$PWD/asf/architecture:/usr/local/structurizr" structurizr/structurizr local
 */
workspace "Agentic Software Forge" "The closed engineering loop, with the Kasten as its root." {

    !identifiers hierarchical

    model {
        author = person "Author" "Plans and assigns the work; decides, judges, merges."

        asf = softwareSystem "Agentic Software Forge" "One OS instance: VM, WSL distribution or container." {
            codingAgent = container "Coding Agent" "Works the item, in several roles." "e.g. Claude Code" "Agent" {
                session = component "Session" "Drives the item through the loop; stops for the author." "Claude Code session" "Agent"
                tester = component "Tester" "Writes the failing tests of a unit." "subagent, superpowers prompt" "Agent"
                implementer = component "Implementer" "Makes the tests pass; changes no test." "subagent, superpowers prompt" "Agent"
                taskReviewer = component "Task reviewer" "Reviews one unit against both rubrics." "subagent, superpowers prompt" "Agent"
                finalReviewer = component "Final reviewer" "Reviews the whole branch." "subagent, superpowers prompt" "Agent"
            }

            harness = container "Harness" "Skills, plugins and settings of the Coding Agent." "Claude Code plugins and settings" {
                devSkills = component "xxthunder-dev-skills" "Skills: closed-loop, backlog-ops, next, logbook, refinement. Scripts: loop.py, backlog.py, board.py, store." "Claude Code plugin" "Plugin"
                superpowers = component "superpowers" "Plans and subagents: writing-plans, subagent-driven-development." "Claude Code plugin" "Plugin"
                jiraSkill = component "Jira skill" "Reads and writes stories in the issue tracker." "Skill" "Plugin"
                mcpServers = component "MCP servers" "Further tools for the Coding Agent." "MCP" "Plugin"
            }

            kasten = container "Kasten" "Contracts, board, log, learnings." "Git repository" "Repository" {
                contracts = component "Contracts" "asf/AGENTS.md: what the skills follow." "Markdown"
                board = component "Board" "engineering/board.md: Next and In Progress." "Markdown"
                logbook = component "Logbook" "engineering/log.md: one line per event." "Markdown"
                generalRubric = component "General rubric" "asf/rubric.md: what every review judges." "Markdown"
                registry = component "Repository registry" "engineering/repos.md: remotes, ID prefixes, gate corrections." "Markdown"
            }

            checkout = container "Repository checkout" "Clone of the target repository with its feature worktree." "Git repository" "Repository"

            devContainer = container "Dev container" "Runs the repository's commands, where it has one." "Dev container"
        }

        provisioner = softwareSystem "Provisioner" "Sets up the instance: Ansible, WSL manager." "External"
        llm = softwareSystem "LLM" "Runs the agents, through a provider's API." "External"
        scm = softwareSystem "SCM" "Remotes, pull requests, checks: GitHub, Gitea …" "External"
        ciServer = softwareSystem "CI server" "Optional: checks pull requests, e.g. Jenkins." "External"
        issueTracker = softwareSystem "Issue tracker" "Ranking, planning, user stories, e.g. Jira." "External"

        # Context
        author -> asf "Assigns work, decides"
        author -> scm "Reviews, merges"
        author -> issueTracker "Plans stories"
        provisioner -> asf "Sets up"
        scm -> ciServer "Runs checks"
        ciServer -> scm "Reports checks"

        # The instance
        provisioner -> asf.codingAgent "Installs"
        provisioner -> asf.harness "Installs"
        asf.codingAgent -> llm "Runs on" "API"
        asf.devContainer -> asf.checkout "Mounts"

        # The author and the session
        author -> asf.codingAgent.session "Starts, answers" "chat"
        author -> asf.kasten.board "Ranks cards" "next put"
        asf.codingAgent.session -> author "Stop: the author decides; Q&A"

        # The session uses the Harness
        asf.codingAgent.session -> asf.harness.devSkills "Skills, guard" "uv run"
        asf.codingAgent.session -> asf.harness.superpowers "Plans, dispatches"
        asf.codingAgent.session -> asf.harness.jiraSkill "Uses"
        asf.codingAgent.session -> asf.harness.mcpServers "Calls" "MCP"
        asf.harness.jiraSkill -> issueTracker "Reads, writes stories"

        # Mechanics through the plugin's scripts
        asf.harness.devSkills -> asf.kasten.contracts "Reads" "store"
        asf.harness.devSkills -> asf.kasten.board "Moves cards" "store"
        asf.harness.devSkills -> asf.kasten.logbook "Writes lines" "store"
        asf.harness.devSkills -> asf.kasten.registry "Resolves repos" "loop.py row"
        asf.harness.devSkills -> asf.checkout "Items, state, guard" "backlog.py, loop.py"

        # The loop: contracts, gate, rubric
        asf.codingAgent.session -> asf.kasten.contracts "Reads"
        asf.codingAgent.session -> asf.kasten.registry "Reads"
        asf.codingAgent.session -> asf.kasten.generalRubric "Hands to reviewers"
        asf.codingAgent.session -> asf.checkout "Gate, worktree, commits, fold" "git, loop.py"
        asf.codingAgent.session -> asf.devContainer "Runs the gate"
        asf.codingAgent.session -> scm "Pushes, opens PR" "git, gh"

        # The roles of one unit
        asf.codingAgent.session -> asf.codingAgent.tester "N.a, disputes"
        asf.codingAgent.session -> asf.codingAgent.implementer "N.b, fix rounds"
        asf.codingAgent.session -> asf.codingAgent.taskReviewer "Per unit"
        asf.codingAgent.session -> asf.codingAgent.finalReviewer "Once, at the end"
        asf.codingAgent.tester -> asf.codingAgent.session "Reports, answers"
        asf.codingAgent.implementer -> asf.codingAgent.session "Reports, disputes"
        asf.codingAgent.tester -> asf.checkout "Commits tests" "git"
        asf.codingAgent.implementer -> asf.checkout "Commits fixes" "loop.py fixup"
        asf.codingAgent.tester -> asf.devContainer "Runs tests"
        asf.codingAgent.implementer -> asf.devContainer "Runs tests"
        asf.codingAgent.taskReviewer -> asf.checkout "Reads diff" "git"
        asf.codingAgent.taskReviewer -> asf.codingAgent.session "Reports findings"
        asf.codingAgent.finalReviewer -> asf.checkout "Reads branch" "git"
        asf.codingAgent.finalReviewer -> asf.codingAgent.session "Reports findings"
    }

    views {
        systemContext asf "Context" "The Agentic Software Forge as one OS instance, and who and what it works with." {
            include *
            include ciServer
        }

        container asf "Containers" "The containers of the instance." {
            include *
            include ciServer
        }

        component asf.codingAgent "CodingAgent" "The roles the Coding Agent runs in: roles of one process." {
            include *
        }

        component asf.harness "Harness" "The plugins of the Harness; their skills and scripts are named in their descriptions." {
            include *
        }

        component asf.kasten "Kasten" "What the loop reads and writes in the Kasten." {
            include *
        }

        dynamic asf "Loop" "One item, from the author's request to the merge. A stop can come at any step: see the Stop edge in Containers." {
            author -> asf.codingAgent "Start the loop for an item"
            asf.codingAgent -> asf.kasten "Reads contracts, registry, general rubric"
            asf.codingAgent -> asf.checkout "Finds the gate and rubric"
            asf.codingAgent -> asf.harness "Pulls the item"
            asf.codingAgent -> author "Optional: Q&A on the plan"
            author -> asf.codingAgent "Optional: answers, into Scope Decisions"
            asf.codingAgent -> asf.checkout "Worktree and plan"
            asf.codingAgent -> asf.checkout "Units 1..n (see Unit), final review"
            asf.codingAgent -> asf.devContainer "Gate; red: at most 2 fix rounds"
            asf.codingAgent -> asf.checkout "Gate green: fold"
            asf.codingAgent -> scm "Push, PR"
            scm -> ciServer "Optional: runs the checks"
            ciServer -> scm "Optional: reports the checks"
            author -> scm "Reviews, merges"
        }

        dynamic asf.codingAgent "Unit" "One unit N of the plan, on its main path." {
            asf.codingAgent.session -> asf.codingAgent.tester "N.a: write failing tests"
            asf.codingAgent.tester -> asf.checkout "Commits the tests"
            asf.codingAgent.session -> asf.codingAgent.implementer "N.b: make them pass"
            asf.codingAgent.implementer -> asf.codingAgent.session "Staged, with message"
            asf.codingAgent.session -> asf.checkout "Commits the code"
            asf.codingAgent.session -> asf.harness "Guard"
            asf.codingAgent.session -> asf.codingAgent.taskReviewer "Review unit N"
            asf.codingAgent.taskReviewer -> asf.codingAgent.session "Findings"
            asf.codingAgent.session -> asf.codingAgent.implementer "Fix round"
            asf.codingAgent.implementer -> asf.checkout "Commits the fix"
        }

        dynamic asf.codingAgent "Dispute" "The implementer holds a test wrong. At most two exchanges, then a stop." {
            asf.codingAgent.implementer -> asf.codingAgent.session "Disputes a test"
            asf.codingAgent.session -> asf.codingAgent.tester "Hands it to a fresh tester"
            asf.codingAgent.tester -> asf.checkout "Fixes the test, or not"
            asf.codingAgent.tester -> asf.codingAgent.session "Fixed, or rejected with a reason"
            asf.codingAgent.session -> asf.codingAgent.implementer "Runs again"
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
        }
    }
}
