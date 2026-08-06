---
name: git-commit-message
description: "Analyze repository changes, separate staged, unstaged, untracked, and partially staged work, then propose logical commit groups and messages. Use when the user requests 'generate commit message', 'create commit', 'git commit', or wants a commit plan for current changes."
---

# Plan Git Commits

## Commit Rules

- Never run `git commit` on your own initiative. When asked to commit or to generate a message, propose the message first and run `git commit` only after the user approves. Ambiguous phrasing like "sync to git" does not mean commit.
- Treat the index as the user's intended commit boundary. When staged changes exist, default the immediate commit proposal to exactly that staged diff; never silently mix unstaged or untracked work into its message or scope.
- Account for staged, unstaged, untracked, partially staged, and relevant submodule changes, but list each path only once under `Scope` or `Not included`. For a partially staged path included in the scope, describe its remaining unstaged hunks in the same entry.
- Do not run `git add`, `git restore --staged`, or otherwise change the index until the user approves an exact commit plan. Never stage an entire partially staged file merely to include one unstaged hunk.
- Always write commit messages in English, even when the conversation is in another language.
- Follow conventional commit format (feat, fix, refactor, docs, test, chore, etc.).
- Keep the title concise (under 50 characters) and in imperative mood ("add", not "added"); mark breaking changes explicitly.
- Use a subject-only message only for small, obvious changes such as typo fixes, formatting-only edits, or narrow single-file docs updates.
- Add a body when the staged change affects behavior, sync/install flows, configuration, security/secrets handling, migration policy, multiple files, multiple repositories/submodules, or when the "why" is not obvious from the title.
- When proposing multiple commits, evaluate each commit independently and include a body for any non-trivial commit.
- Do NOT add AI co-author trailers (e.g., `Co-Authored-By: Claude`, `Co-Authored-By: Codex`) or generator footers (e.g., `🤖 Generated with ...`).

## Workflow

1. Read the repository's applicable agent instructions and commit rules. Respect repository boundaries and required submodule commit order.
2. Inventory the whole working tree with `git status --short`. Classify every relevant path as staged, unstaged, untracked, partially staged, or a submodule state. A path with both index and worktree changes belongs in the partially staged group.
3. Inspect the staged diff in detail with `git diff --staged`. Always know the paths and statuses of other changes, but inspect their content only when:
   - nothing is staged,
   - they are needed to understand the staged change,
   - they are the unstaged portion of a partially staged file,
   - they appear related to the proposed commit,
   - they were created or modified by this agent in the current session, or
   - a submodule's inner state and parent pointer need to be distinguished.
4. Do not open likely secret or credential files merely because they are untracked. Report the path and risk instead.
5. Determine the proposed commit scope:
   - When staged changes exist, use exactly the staged diff as the default immediate scope.
   - When nothing is staged, select exact files or hunks based on work completed in the current session and logical cohesion.
   - Put every remaining relevant path under **Not included**, with its current state, a brief description, and why it is excluded or what should happen next.
6. If staged changes contain unrelated concerns, recommend splitting them and explain why, but do not alter the index. Recommend related unstaged or untracked additions when needed for completeness, but keep them outside a staged scope until approved.
7. For each proposed commit, state its exact scope, briefly summarize each included change, explain why the changes belong together when it is not obvious, and provide a commit message.
8. Present the proposal using the format below, then wait for approval.
9. After approval, apply only the approved staging changes. Re-check `git status --short` and `git diff --staged` immediately before committing; if the staged scope changed from the approved plan, stop and propose the updated plan instead.
10. After committing, report the commit hash and the remaining staged, unstaged, untracked, and submodule state.

## Response Format

````markdown
## Proposed Commit

Scope:
- [file-a.ext](absolute/path/to/file-a.ext) — [brief change summary]
- [file-b.ext](absolute/path/to/file-b.ext) — [brief change summary]

Why: [brief explanation; omit when obvious]

Message:

```
type: brief description

(body only when non-trivial: explain relevant why/how and behavior, policy,
migration, or safety impact)
```

## Not included

- [file-c.ext](absolute/path/to/file-c.ext) (unstaged) — [brief description]; [why it is excluded or suggested next step]
- [notes.md](absolute/path/to/notes.md) (untracked) — [brief description]; [why it is not worth committing]

Omit `Not included` when no relevant changes remain outside the proposed scope. When multiple commits are needed, repeat the scope and message for each commit. Write the analysis in the user's preferred language.

Wait for the user to approve or revise the scope and message. Do not stage or commit while presenting this proposal.
````
