---
name: handoff
description: "Use this skill when the user requests a durable, self-contained handoff of the current work for a fresh session or another coding agent. Trigger on requests like \"handoff\", \"save context\", \"summary for next session\", \"export conversation\", \"save work state\", or any request to preserve enough intent, decisions, verified state, constraints, and next actions for later continuation without access to the original session. Do NOT use for general summarization, code explanation, or documentation unrelated to handing work off."
---

# Handoff

## Purpose

Create a durable recovery artifact so a fresh session — another Claude instance or a different coding agent — can reproduce the work's intent, decisions, verified state, constraints, and next actions without access to the original session.

A handoff complements session resume or compaction; it does not replace an intact original session. Its distinct value is to preserve session-only context in a tool-neutral, project-local file and anchor that context to the live state of the work.

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

1. **Check existing handoffs** (when continuing work): search any date-prefixed folder for the task — `ls -dt .handoffs/*-{task-slug} 2>/dev/null | head -5`. Read the most recent handoff file **regardless of author prefix** and integrate any still-relevant context so the new handoff remains self-contained. Reference the previous file for provenance, but do not require the next agent to follow a chain of handoffs.
2. **Recover the session's intent**:
   - State the user's goal and concrete success criteria.
   - Preserve explicit constraints, preferences, approval gates, and "do not" instructions. Use the user's exact wording when paraphrasing could change the meaning.
   - Record decisions with their rationale, plus rejected or deferred alternatives and why they were not chosen.
   - Capture discoveries, failed approaches, and other context that exists only in the conversation rather than the repository.
3. **Verify the live state before writing**:
   - Identify the workspace/repository root and, when applicable, the current branch and `HEAD`.
   - Inspect the current worktree state and relevant diffs; distinguish staged, unstaged, untracked, and committed work when that distinction matters.
   - Confirm that referenced files and paths still exist.
   - Record the exact validation commands already run and their observed results. Re-run only safe, relevant checks when needed to avoid recording stale claims.
   - Do not mutate, sync, commit, or otherwise change the work merely to prepare the handoff.
4. **Separate kinds of knowledge**:
   - **Verified state** — directly observed in files, Git state, command output, or an authoritative source.
   - **User/session decisions** — explicitly stated or agreed in the conversation.
   - **Inference or assumption** — plausible but not confirmed; say what would verify it.
   - **Open question** — requires the user, another agent, or a future check.
5. **Create the handoff file** at the path above, following [references/handoff-template.md](references/handoff-template.md). Include a source session ID/link only when one is available; the handoff must still stand alone without it.
6. **Audit for resumability**: assume the reader cannot see the original conversation. Confirm that the file alone explains what the user wants, what is true now, why key decisions were made, what must not be done, what remains uncertain, and exactly how to continue and verify the next action.
7. **Report back**: give the user the file path and a brief overview of what was captured.

## Writing Checklist

- [ ] User goal, success criteria, scope, and non-goals clear?
- [ ] Explicit preferences, constraints, approval gates, and prohibitions preserved?
- [ ] Accepted decisions and rejected/deferred alternatives include their rationale?
- [ ] Session-only discoveries and failed approaches recorded?
- [ ] Live state anchored to a verification time, repo root, branch/`HEAD`, and worktree state where applicable?
- [ ] Verified facts, user decisions, inferences, and open questions clearly distinguished?
- [ ] Completed (✅) / in-progress (🔄) / pending (⏳) tasks distinguished?
- [ ] Relevant files and validation results named precisely?
- [ ] Next steps include accurate paths, commands or concrete actions, expected results, and stop/approval conditions?
- [ ] Previous handoff integrated and referenced without making it required reading?

## Best Practices

- **Optimize for recovery, not minimum length**: include all continuation-critical context. Longer is preferable to omitting a constraint, rationale, failed path, or state detail that the next agent would otherwise have to rediscover. Remove repetition only when it adds no information.
- **Preserve what the repository cannot**: prioritize user intent, decision rationale, rejected alternatives, approval boundaries, and lessons from failed attempts. Link to repository documentation instead of copying it unless its current implication is itself important.
- **Use stable anchors**: exact file paths, symbols, commit IDs, commands, and observed results. Do not rely on volatile line numbers or conversational references such as "the previous option" without restating them.
- **Be operational**: the next agent should be able to verify drift and start the next action without rereading the original conversation.
- **Be explicit about uncertainty**: never turn an inference, remembered claim, or stale external state into a verified fact.
- **Write tool-neutral**: the reader may not be a Claude instance. Avoid instructions that only work in this tool.
- **Match the user's language**: write the handoff in the user's explicitly requested language; if no language is specified, write it in the user's preferred language.
