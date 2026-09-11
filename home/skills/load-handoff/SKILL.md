---
name: load-handoff
description: "Use this skill when the user wants to resume work from a previous handoff file. Trigger on requests like \"continue from handoff\", \"resume work\", \"load handoff\", \"resume from handoff\", or when the user provides a handoff file path. Use when the user wants to continue previous work without losing context. The user can provide a handoff file path as an argument, either as a relative path or using @ file reference (e.g., /load-handoff .handoffs/YYMMDD-task-name/claude-handoff-xxx.md or /load-handoff @claude-handoff-xxx.md). Do NOT use for general file reading or tasks unrelated to resuming previous work."
disable-model-invocation: true
---

# Resume Work from Handoff

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
5. **Summarize the restored context and drift** to the user, covering the items in Report below. Do not silently replace the recorded state with the current state; explain material differences.
6. **Propose the next action**. If the user asked only to load or inspect the handoff, wait for approval before executing it. If the user explicitly asked to resume or continue the recorded work, that authorizes safe next actions already within the handoff's scope; still honor every recorded approval gate and stop condition.

If work remains when the session is ending, suggest creating a new handoff with the handoff skill; write one only when the user asks.

## Report

Cover every item below in the summary to the user. The layout is free, but do not drop an item; write "none" when it does not apply.

- Task and the handoff file path
- Recorded state vs current state, with any drift
- Success criteria
- Must-not-do constraints and approval gates
- Accepted and rejected decisions
- Work progress, split into completed, in progress, and pending
- Unverified claims
- First next action, with its expected result and stop condition

## Error Handling

- **Invalid format** (missing enough information to identify the task, current/progress state, and next steps): warn that the file doesn't look like a complete handoff, summarize what is there, identify the missing continuation context, and ask whether to proceed.
