---
name: load-handoff
description: "Use this skill when the user wants to resume work from a previous handoff file. Trigger on requests like \"continue from handoff\", \"resume work\", \"load handoff\", \"resume from handoff\", or when the user provides a handoff file path. Use when the user wants to continue previous work without losing context. The user can provide a handoff file path as an argument, either as a relative path or using @ file reference (e.g., /load_handoff .handoffs/YYMMDD-task-name/claude-handoff-xxx.md or /load_handoff @claude-handoff-xxx.md). Do NOT use for general file reading or tasks unrelated to resuming previous work."
---

# Resume Work from Handoff

## Purpose

Load a handoff file from a previous session to restore the work context and continue from where it was left off.

## Workflow

1. **Resolve the file path** from args:
   - Absolute path → use as-is; relative path → resolve from workspace root; `@` file reference → already converted to absolute path
   - No path provided → list candidates with `ls -lt .handoffs/*/` and ask the user which one to load
2. **Read the handoff file**. Handoffs may be from Claude or other agents (`codex-handoff-*.md`, etc.). Treat the file as self-contained even when it links to a source session or previous handoff; follow those references only when the current handoff identifies a genuine gap or the user asks.
3. **Reconstruct the working model**:
   - User goal, success criteria, scope, and non-goals
   - Explicit preferences, prohibitions, and approval gates
   - Accepted decisions and their rationale
   - Rejected or deferred alternatives and the conditions for revisiting them
   - Completed, in-progress, and pending work
   - Session-only discoveries, failed approaches, assumptions, and open questions
   - Next actions, their expected results, and their stop conditions
4. **Verify against the live state**: the handoff reflects a past state. Compare its recorded verification time, workspace, branch, `HEAD`, worktree state, referenced files, and relevant external state with the current environment. Re-run safe checks that materially affect the next action. Distinguish:
   - still-current verified facts
   - meaningful drift since the handoff
   - assumptions or claims that remain unverified
   - user/session decisions that remain binding regardless of repository drift
5. **Summarize the restored context and drift** to the user using the response template below. Do not silently replace the recorded state with the current state; explain material differences.
6. **Propose the next action**. If the user asked only to load or inspect the handoff, wait for approval before executing it. If the user explicitly asked to resume or continue the recorded work, that authorizes safe next actions already within the handoff's scope; still honor every recorded approval gate and stop condition.

If additional work remains after resuming, create a new handoff (via the handoff skill) to maintain continuity.

## Response Template

```markdown
## 📋 Work Context Restored

**Task**: [Task Overview summary]
**Handoff File**: [file path]
**Recorded State**: [verification time, branch/HEAD when applicable]
**Current State**: [matching or material drift]

### User Intent and Boundaries

- **Success criteria**: [summary]
- **Must preserve / must not do**: [constraints and approval gates]

### Decisions to Carry Forward

- **Accepted**: [decision and rationale]
- **Rejected/deferred**: [alternative and reason]

### Progress

**Completed (✅)**:
- [Completed task]

**In Progress (🔄)**:
- [In-progress task]

**Pending (⏳)**:
- [Pending task]

### Identified Issues

1. [Issue 1]

### Drift and Unverified Claims

- [Recorded claim that changed or still requires verification]

### Next Steps

[First next action, expected result, and stop/approval condition]

---

**Ready to start the next task?**
- Task: [First item in Next Steps]
- File: [Related file path]
```

## Error Handling

- **File not found**: report the bad path and suggest `ls -lt .handoffs/` to locate available handoffs.
- **Invalid format** (missing enough information to identify the task, current/progress state, and next steps): warn that the file doesn't look like a complete handoff, summarize what is there, identify the missing continuation context, and ask whether to proceed.
- **No path provided**: show usage (`/load_handoff <path>` or `/load_handoff @file`) and list available handoffs.
