---
name: setup-team-agents
description: "Design and spawn a collaborative team of agents. Invoke with '/setup-team-agents <description>'. Analyzes the description, designs 3-5 agents with distinct perspectives and expertise, and sets up a multi-round feedback collaboration structure. Only spawns agents — does NOT start work. Waits for the user's explicit go-ahead. Also triggers on 'set up team agents', 'create agent team', 'build a swarm', 'collaborative agent setup', etc. Do NOT use for tasks a single agent can handle, simple subagent delegation, or when the user just wants quick research — this skill is for complex problems that benefit from multiple distinct perspectives debating each other."
compatibility: Requires Claude Code with experimental team agents feature enabled (experimentalTeamAgents)
---

# Setup Team Agents

Design and spawn a collaborative agent team to tackle the given task.
After spawning, wait for the user's explicit instruction before starting any work.

## Input

```
/setup-team-agents <description>
```

If the description is missing or ambiguous, ask the user to clarify the task.

## Workflow

### 1. Analyze the Task

Extract from the description:

- Core objective and scope
- Required areas of expertise (technical, domain, perspective)
- Expected decision points and trade-offs
- Key quality criteria

### 2. Design the Team

Design 3–5 agent roles. If the user specifies a different count, follow that.

**Design philosophy**: Do NOT split work into sequential phases. Instead, divide by **distinct perspectives and expertise**. Different viewpoints naturally produce disagreement, feedback, and iteration.

Bad — phase-based split:
```
agent-1: research  →  agent-2: design  →  agent-3: implement  →  done
```
Each agent works in isolation and finishes without interaction.

Good — perspective-based split:
```
researcher: focuses on evidence, data, and current state
architect: prioritizes structure, extensibility, and elegance
pragmatist: challenges feasibility, cost, and complexity
critic: hunts for gaps, risks, and blind spots
synthesizer: integrates all perspectives into a coherent conclusion
```
This way, the architect's proposal gets challenged by the pragmatist on feasibility, the critic pokes holes, and the researcher provides evidence — natural round-trips emerge.

**Required role — synthesizer**:
Always include a dedicated agent responsible for final integration, conclusions, and deliverables. The main agent (you) must NOT take on this role. The synthesizer collects all artifacts and discussions from other agents and produces the final output.

**Checklist for role design**:
- Do at least 2 pairs of agents have a natural tension or complementary relationship?
- Are the perspectives distinct enough from each other?
- Does each agent have a reason to read and respond to another agent's work?

### 3. Design the Collaboration Flow

Design inter-agent interactions. The core principle is **round-trips**, not one-way pipelines.

Include at least 2–3 rounds of back-and-forth feedback:

```
[Round 1] Each specialist drafts initial opinions/proposals from their perspective
[Round 2] Agents read each other's drafts, send feedback/challenges/requests
[Round 3] Agents revise based on feedback, counter-argue if needed
[Round 4] Synthesizer collects all artifacts and discussions, produces final output
```

Create tasks matching this round structure and set `blockedBy` dependencies accordingly.

### 4. Artifact Naming Convention

All intermediate artifacts are saved as `.md` files in the workspace folder, using this pattern:

```
r{round}-{agent}-{type}.md
```

- **r{round}**: Round number (`r1`, `r2`, `r3`, `r4`)
- **{agent}**: Name of the agent who authored the file
- **{type}**: Content type — one of:
  - `draft` / `analysis` / `proposal` — initial work in round 1
  - `review-{target}` — feedback on another agent's work (target = reviewed agent's name)
  - `revision` — updated version incorporating feedback
  - `final` — synthesizer's integrated output

**Example file listing:**
```
r1-researcher-analysis.md
r1-architect-proposal.md
r2-critic-review-architect.md
r2-pragmatist-review-researcher.md
r3-architect-revision.md
r3-researcher-revision.md
r4-synthesizer-final.md
```

Files naturally sort by round, making the collaboration timeline easy to follow. Include this convention in every agent's prompt so all agents produce consistently named artifacts.

### 5. Prepare the Workspace

Create a working directory under `.teams/` in the project root:

```
.teams/YYMMDD-<task-slug>/
```

- **YYMMDD**: Today's date in KST. Run `TZ='Asia/Seoul' date +"%y%m%d"` to get it.
- **task-slug**: Short name extracted from the description. Lowercase, hyphens for spaces.
  - e.g., "API auth refactoring" → `api-auth-refactoring`

Save `team-design.md` in this folder:

```markdown
# Team Design: {one-line task summary}

> **Task**: {description}
> **Date**: {YYYY-MM-DD}
> **Team name**: {team-name}

## Agent Roster

| Agent | Role | Perspective/Expertise | Key Interactions |
|-------|------|-----------------------|------------------|
| {name} | {one-line description} | {focus area} | {who they interact with and how} |

## Collaboration Flow

{Round-by-round interaction flow, as text or diagram}

## Task List

{Created tasks and their dependency relationships}

## Artifact Plan

{Planned .md files per round, with brief content descriptions}
```

### 6. Create Team and Tasks

1. **TeamCreate** to create the team
   - `team_name`: same as the workspace folder name (`YYMMDD-<task-slug>`)

2. **TaskCreate** for each round's tasks
   - Structure tasks by round
   - Set `blockedBy` to enforce round ordering
   - Leave all tasks as `pending` with no `owner`
   - Include the output filename and workspace path in each task's description

### 7. Spawn Agents

Spawn each agent using the `Agent` tool.

**Agent tool parameters**:
- `team_name`: the created team name
- `name`: the designed role name
- `subagent_type`: default to `general-purpose` — all agents that produce workspace artifacts need the Write tool. Only use `Explore` or `Plan` for roles that never create files and communicate exclusively via SendMessage.
- `run_in_background: true` (spawn all agents in the background)

**Agent prompt guide**:

Each agent's prompt should include:

1. **Identity**: "You are {role-name} on the {team-name} team. {detailed role description}."
2. **Perspective**: "Your perspective focuses on {perspective description}. You approach the task from this angle."
3. **Collaboration**: "You primarily interact with {target agents}. {specific interaction patterns}."
4. **Artifact rules**: "Save all work artifacts as .md files in `.teams/{workspace-name}/` using the naming convention `r{round}-{your-name}-{type}.md` (e.g., `r1-architect-proposal.md`, `r2-critic-review-architect.md`)."
5. **Behavior**: "Check TaskList to find tasks assigned to you. Read other agents' artifacts from the workspace folder. Send feedback and opinions directly to other agents via SendMessage."

Spawn all agents **concurrently** whenever possible (multiple Agent calls in a single message).

### 8. Report and Wait

Once all agents are spawned, report to the user:

```
## Team Ready

**Team**: {team-name}
**Workspace**: .teams/{workspace-name}/

| Agent | Role | Status |
|-------|------|--------|
| {name} | {one-line description} | spawned |

### Collaboration Flow
{round-by-round summary}

### Tasks Created
{task list with dependencies}

---
Give the word to start.
```

Then **do NOT start any work on your own**. Wait for the user's explicit instruction.

## When the User Says Go

When the user gives the go-ahead ("start", "go", "proceed", etc.):

### Kick Off

1. Assign Round 1 tasks to agents (TaskUpdate with `owner`)
2. Send a start message to each agent via SendMessage with their task context and workspace path

### Orchestrating Rounds

The main agent orchestrates the collaboration through rounds.

**Round transition flow**:

1. When an agent completes (background notification), check TaskList for the current round's status
2. When all tasks in the round are complete, post a brief progress update:

```
### Round {N} Complete
- {agent}: {one-line summary}
- {agent}: {one-line summary}
```

3. **If you can proceed without user confirmation** (user pre-approved all rounds, or operating in autonomous mode) → assign next round's tasks immediately and continue
4. **Otherwise** → report progress and wait for the user's instruction before starting the next round

**Always pause for the user**, regardless of permission level, when:
- Agents reach conflicting conclusions that affect the overall direction
- Scope or requirements need mid-course clarification
- An agent fails or cannot complete its task

### Final Delivery

When the synthesizer completes:

1. Read the synthesizer's final artifact from the workspace
2. Present a summary to the user with a pointer to the full `.md` file
3. Ask if the user wants revisions, additional rounds, or is satisfied

## Must Use Team Agents — Not Subagents

This skill requires the full team workflow. Do NOT substitute with simpler patterns:

- **Wrong — bare subagents**: Spawning agents via the Agent tool without TeamCreate. This skips the shared task list, team coordination, and inter-agent messaging infrastructure.
- **Wrong — inline work**: Doing the work yourself (the main agent) instead of spawning a team. Even if the task seems simple enough to handle alone, this skill was explicitly invoked to set up a team.
- **Wrong — single orchestrator + workers**: Spawning one "smart" agent that does all the thinking while others just execute. Every agent should have a real perspective and voice.

The correct sequence is always: **TeamCreate → TaskCreate → Agent (with `team_name`)**.  
If any of these three steps is missing, the setup is incomplete.

## Guidelines

- Don't force unnecessary roles. If 3 agents suffice, use 3.
- Write agent prompts in the user's language (match the conversation language), except for code/technical terms.
- Workspace .md files double as asynchronous communication channels — agents save artifacts to files, and other agents read them for feedback.

## Error Handling

- **No description provided**: Ask the user to describe the task before proceeding.
- **Team feature unavailable**: If TeamCreate fails (e.g., `experimentalTeamAgents` not enabled in settings), inform the user and explain how to enable it.
- **Agent spawn failure**: Report which agent failed. Retry once; if it fails again, proceed with the remaining agents and note the coverage gap to the user.
- **Task stuck**: If a task shows no progress after other agents in the same round have completed, send a follow-up via SendMessage. If still unresponsive, report to the user and suggest proceeding without that agent's input.
