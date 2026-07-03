---
name: handoff
description: "Use this skill when the user requests a handoff or summary of the current conversation context for continuing work in a fresh session. Trigger on requests like \"handoff\", \"save context\", \"summary for next session\", \"export conversation\", \"save work state\", or any request to capture the current state of work for later continuation. Use when the user wants to transfer context to a new Claude instance or another coding agent, save progress before ending a session, or provide a summary for another agent to continue the task. Do NOT use for general summarization, code explanation, or documentation unrelated to handoff purposes."
---

# Handoff

## Purpose

Capture the current conversation context so a fresh session — another Claude instance or a different coding agent — can continue the work without missing information.

## Storage Convention

Handoffs live in the **project root's** `.handoffs/` directory, shared across coding agents:

```
.handoffs/YYMMDD-{task-slug}/claude-handoff-YYYY-MM-DD-HHMMSS.md
```

- `YYMMDD` (folder date) — KST: `TZ='Asia/Seoul' date +"%y%m%d"`
- `{task-slug}` — task name from the conversation, lowercase, hyphens for spaces
- `claude-` filename prefix identifies the author, so handoffs from other agents (e.g. `codex-handoff-*.md`) can share the same task folder
- Timestamp — KST: `TZ='Asia/Seoul' date +"%Y-%m-%d-%H%M%S"`. If the exact filename already exists, append `-2`, `-3`, ...
- **NEVER** save under `~/.claude/` (global folder). The project-level `.handoffs/` keeps handoffs project-specific, out of auto-loaded context, and git-trackable when desired.

## Workflow

1. **Check existing handoffs** (when continuing work): search any date-prefixed folder for the task — `ls -dt .handoffs/*-{task-slug} 2>/dev/null | head -5`. Read the most recent handoff file **regardless of author prefix** and reference it in the new one for continuity.
2. **Analyze the conversation**: tasks attempted, what worked, what didn't, current state.
3. **Create the handoff file** at the path above, following the structure in [references/handoff-template.md](references/handoff-template.md).
4. **Report back**: give the user the file path and a brief overview of what was captured.

## Writing Checklist

- [ ] Task overview clear?
- [ ] Completed (✅) / in-progress (🔄) / pending (⏳) tasks distinguished?
- [ ] Identified issues listed?
- [ ] Next steps include executable code with accurate file paths?
- [ ] Failures and lessons recorded? Knowing what didn't work matters as much as what worked
- [ ] Previous handoff referenced (if continuing work)?

## Best Practices

- **Be specific**: exact file paths, code, and commands — the next agent should start immediately without rereading the full conversation.
- **Keep it concise**: 100–300 lines. Enough detail to continue, not a transcript.
- **Write tool-neutral**: the reader may not be a Claude instance. Avoid instructions that only work in this tool.
- **Match the user's language**: write the handoff in the user's explicitly requested language; if no language is specified, write it in the user's preferred language.
