---
name: make-plan
description: "Create a versioned implementation plan as a markdown file in the workspace's .plans/ directory."
disable-model-invocation: true
---

# Make Plan

## Purpose

Save implementation plans as markdown files in the workspace's `.plans/` directory.
Plans are meant to be reviewed by the user and referenced by future Claude sessions or other coding agents.

## Workflow

1. **Locate the plan**: if a folder for this task already exists, use it and pick the next version as described in Version Management. Otherwise create a new folder: derive a lowercase, hyphen-separated slug from the description and prefix it with the KST date from `TZ='Asia/Seoul' date +"%y%m%d"`.
2. **Ground the plan**: explore the relevant code, and gather the conversation context (problems found, attempts, conclusions) for the required Context section. Read any referenced files, documents, external material, or prior plans from any author, verify their claims against the current code, and do not copy unverified claims into the plan.
3. **Write and report**: create the markdown file and report its path with a short summary.

If plan mode is active, the `.plans/` file cannot be written yet: present the plan the way plan mode asks, and create the `.plans/` file after the user approves the plan and plan mode ends.

## File Naming Convention

```
.plans/YYMMDD-{task-name}/claude-plan.md        # first plan
.plans/YYMMDD-{task-name}/claude-plan-v2.md     # revised plan
.plans/YYMMDD-{task-name}/claude-plan-v3.md     # further revisions
```

- Filenames must start with `claude-` so other coding agents can identify the author
- Folder name is KST date prefix + slug derived from the description (e.g., "Add API auth" on 2026-04-13 → `260413-api-auth`)
- First file has no version suffix; subsequent files use v2, v3, etc.

## Version Management

When revising or building on an existing plan:

1. Find the task's existing folder. Match it by meaning, not only by an exact slug, because another session may have derived a slightly different slug for the same task; list `.plans/` when unsure
2. List all files in the task folder
3. Read the latest file to understand the previous plan
4. Create a new file with the next version number in that same folder — never modify existing files, even when revising a plan created earlier in the same session
5. Reference the previous version at the top of the new file

If plan files from other agents already exist (e.g., `codex-plan.md`, `cursor-plan.md`), continue the version sequence from where they left off. Read those files first, then create `claude-plan-v{N}.md` as the next version.

```bash
# Check existing files (including files from other agents)
# Find the task folder under any date prefix
ls -d .plans/[0-9][0-9][0-9][0-9][0-9][0-9]-{task-name}/ 2>/dev/null

# Version examples
# claude-plan.md only             → claude-plan-v2.md
# claude-plan-v2.md exists        → claude-plan-v3.md
# codex-plan.md only              → claude-plan-v2.md (continues from codex)
# codex-plan.md + claude-plan-v2  → claude-plan-v3.md
```

## Plan Template

When using this template, translate headings and prose into the user's explicitly requested language; if no language is specified, use the user's preferred language. Keep file paths, code identifiers, and commands unchanged.

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
