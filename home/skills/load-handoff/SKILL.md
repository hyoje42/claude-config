---
name: load-handoff
description: "Resume work from a .handoffs/ handoff file: restore its context, check drift against the live state, and propose the next action."
disable-model-invocation: true
---

# Resume Work from Handoff

## Workflow

1. **Find the handoff file** from the arguments:
   - If an `@` reference already attached the file, use that content instead of reading it again; otherwise resolve a relative path from the workspace root.
   - No path provided → list candidates newest first with `ls -lt .handoffs/*/*-handoff-*.md` and ask the user which one to load
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
6. **Propose the next action and wait**. Do not start the recorded work on your own, even when the user asked to resume or continue; the user decides after seeing the drift report. Approvals recorded in the handoff came from another session, so ask again before any commit, sync, push, or other gated action, and honor every recorded approval gate and stop condition.

If work remains and the user says they are stopping or switching tools, suggest creating a new handoff with the handoff skill; write one only when the user asks.

## Report

Cover every item below in the summary to the user. The layout is free, but do not drop an item; write "none" when it does not apply.

- Task and the handoff file path
- Recorded state vs current state, with any drift
- Success criteria
- Must-not-do constraints and approval gates
- Accepted and rejected decisions
- Work progress, split into completed, in progress, and pending
- Unverified claims
- Open questions and decisions the user must make, with what each blocks
- First next action, with its expected result and stop condition

## Error Handling

- **Invalid format** (missing enough information to identify the task, current/progress state, and next steps): warn that the file doesn't look like a complete handoff, summarize what is there, identify the missing continuation context, and ask whether to proceed.
