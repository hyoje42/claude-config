---
name: make-plan
description: "Create an implementation plan as a markdown file in the workspace's .plans/ directory. Trigger on '/make-plan {description}' or when the user asks to 'create a plan', 'write a plan', 'plan this out', or similar requests to formalize an approach before implementation. Do NOT trigger for casual discussion about plans or when the user just wants verbal advice."
---

# Make Plan

## Purpose

Save implementation plans as markdown files in the workspace's `.plans/` directory.
Plans are meant to be reviewed by the user and referenced by future Claude sessions or other coding agents.

## Workflow

1. **Analyze description**: Understand what needs to be planned from the user's description
2. **Gather context**: Summarize problems found, discussion points, and attempts from the conversation so far
3. **Explore the codebase**: Investigate relevant code and project structure needed for planning
4. **Verify references**: If any files, documents, or prior plans are referenced, read them and cross-check against the actual code. Never trust reference material without verification.
5. **Determine task name**: Extract a slug from the description (lowercase, hyphen-separated)
6. **Check versions**: Look for existing plan files in the task folder and determine the next version number
7. **Write the plan**: Create the markdown file
8. **Report back**: Show the file path and a brief summary to the user

## File Naming Convention

```
.plans/{task-name}/claude-plan.md        # first plan
.plans/{task-name}/claude-plan-v2.md     # revised plan
.plans/{task-name}/claude-plan-v3.md     # further revisions
```

- Filenames must start with `claude-` so other coding agents can identify the author
- Task name is a slug derived from the description (e.g., "Add API auth" → `api-auth`)
- First file has no version suffix; subsequent files use v2, v3, etc.

## Version Management

When revising or building on an existing plan:

1. List all files in the task folder
2. Read the latest file to understand the previous plan
3. Create a new file with the next version number — never modify existing files
4. Reference the previous version at the top of the new file

If plan files from other agents already exist (e.g., `codex-plan.md`, `cursor-plan.md`), continue the version sequence from where they left off. Read those files first, then create `claude-plan-v{N}.md` as the next version.

```bash
# Check existing files (including files from other agents)
ls .plans/{task-name}/ 2>/dev/null

# Version examples
# claude-plan.md only             → claude-plan-v2.md
# claude-plan-v2.md exists        → claude-plan-v3.md
# codex-plan.md only              → claude-plan-v2.md (continues from codex)
# codex-plan.md + claude-plan-v2  → claude-plan-v3.md
```

## Plan Template

```markdown
# {Task Title}

> **Description**: {original description from user}
> **Date**: {YYYY-MM-DD}
> **Version**: v1 (or v2, v3...)
> **Previous**: {path to previous version, if any}

## Overview

[Goal of this plan in 1-3 sentences]

## Context

[Why this work is needed. Summarize the conversation: problems discovered, what was tried, conclusions reached. Write so that someone with no prior context — a future Claude session or another developer — can understand the motivation.]

## Current State

[Analysis of the current code/system. Include relevant file paths.]

## Implementation Plan

### Phase 1: {title}

1. **{task}**
   - File: `path/to/file`
   - Change: [specific change description]

2. **{task}**
   - File: `path/to/file`
   - Change: [specific change description]

### Phase 2: {title}

[Add as many phases as needed]

## Key Decisions

- [Design decisions and their rationale]

## Risks & Considerations

- [Potential issues and things to watch out for]

## Out of Scope

- [What this plan intentionally does not cover]
```

## Rules

- Plans must be concrete and actionable — include exact file paths and specific changes, not vague instructions
- Explore the codebase thoroughly before writing the plan
- **Never blindly trust references.** When files, documents, prior plans, or external material are provided, verify them against the actual code before incorporating. Confirm that file paths exist, functions/classes are real, and descriptions match current state. Do not copy unverified claims into the plan.
- Always include the Context section with conversation background — problems found, things tried, conclusions reached
- Never modify existing plan files — always create a new version
- **If `/make-plan` is called again for the same task within the same session, always create a new versioned file** — never overwrite
- Create `.plans/` in the workspace root
- Report the file path to the user after writing
