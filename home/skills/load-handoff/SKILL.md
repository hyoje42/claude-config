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
2. **Read the handoff file**. Handoffs may be written by another agent (`codex-handoff-*.md`, etc.) — treat them the same as Claude-authored ones. The standard structure is described in the handoff skill's `references/handoff-template.md`.
3. **Analyze the context**: task overview, current progress, identified issues, key file modifications, notes (what worked / what failed), next steps.
4. **Verify against the code**: the handoff reflects a past state. Spot-check that referenced files exist and progress claims still match the current codebase before acting. Do not trust stale claims.
5. **Summarize status** to the user using the response template below.
6. **Propose next action** and execute Next Steps only after user approval, one task at a time.

If additional work remains after resuming, create a new handoff (via the handoff skill) to maintain continuity.

## Response Template

```markdown
## 📋 Work Context Restored

**Task**: [Task Overview summary]
**Handoff File**: [file path]

### Progress

**Completed (✅)**:
- [Completed task]

**In Progress (🔄)**:
- [In-progress task]

**Pending (⏳)**:
- [Pending task]

### Identified Issues

1. [Issue 1]

### Next Steps

[Summary of Next Steps content]

---

**Ready to start the next task?**
- Task: [First item in Next Steps]
- File: [Related file path]
```

## Error Handling

- **File not found**: report the bad path and suggest `ls -lt .handoffs/` to locate available handoffs.
- **Invalid format** (missing Task Overview / Current Progress / Next Steps): warn that the file doesn't look like a handoff, summarize what is there, and ask whether to proceed.
- **No path provided**: show usage (`/load_handoff <path>` or `/load_handoff @file`) and list available handoffs.
