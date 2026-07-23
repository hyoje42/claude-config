---
name: git-commit-message
description: "Analyze repository changes, separate staged, unstaged, untracked, and partially staged work, then propose logical commit groups and messages. Use when the user requests 'generate commit message', 'create commit', 'git commit', or wants a commit plan for current changes."
---

# Plan Git Commits

## Commit Rules

- Never run `git commit` on your own initiative. When asked to commit or to generate a message, propose the message first and run `git commit` only after the user approves. Ambiguous phrasing like "sync to git" does not mean commit.
- Treat the index as the user's intended commit boundary. When staged changes exist, default the immediate commit proposal to exactly that staged diff; never silently mix unstaged or untracked work into its message or scope.
- Always report staged, unstaged, untracked, partially staged, and relevant submodule states, even when the proposed commit uses only staged changes.
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
5. Build logical groups:
   - **Current staged commit**: when staged changes exist, propose exactly those changes as the default immediate commit.
   - **Related inclusion candidates**: unstaged or untracked work that appears necessary for completeness, especially relevant tests, docs, generated files, or changes made in this session. Recommend inclusion, but keep it outside the staged commit until approved.
   - **Follow-up commits**: coherent changes that should be committed separately.
   - **Hold/exclude**: unrelated, user-owned, risky, or unclear changes that should remain untouched.
6. If staged changes contain unrelated concerns, recommend splitting them and explain why, but do not alter the index. If nothing is staged, propose exact files for each logical commit, prioritizing changes made in this session while clearly flagging pre-existing user changes.
7. For each proposed commit, state its exact scope, explain why those changes belong together, and provide a commit message. Make a direct recommendation such as: "I propose committing A and B now as `...`, keeping C for a follow-up."
8. Present the full state and commit plan using the format below, then wait for approval.
9. After approval, apply only the approved staging changes. Re-check `git status --short` and `git diff --staged` immediately before committing; if the staged scope changed from the approved plan, stop and propose the updated plan instead.
10. After committing, report the commit hash and the remaining staged, unstaged, untracked, and submodule state.

## Response Format

````markdown
## Change State

### Staged — current commit candidate
- [file-a.ext](absolute/path/to/file-a.ext) (modified)

### Unstaged — not in the current commit
- [file-b.ext](absolute/path/to/file-b.ext) (modified)

### Untracked — new files
- [file-c.ext](absolute/path/to/file-c.ext)

### Partially staged / submodules
- [file-d.ext](absolute/path/to/file-d.ext) — has both staged and unstaged hunks
- [submodule](absolute/path/to/submodule) — describe inner changes and parent pointer separately

Omit empty groups. Write this analysis in the user's preferred language.

## Proposed Commit Plan

### Commit 1 — commit now

Scope:
- file-a.ext
- staged hunks of file-d.ext

Why these belong together:
- [brief explanation]

Message:

```
type: brief description

(body only when non-trivial: explain relevant why/how and behavior, policy,
migration, or safety impact)
```

### Related inclusion candidates
- file-c.ext — [why it may belong in Commit 1, and that it is not staged]

### Follow-up commits
- Commit 2: file-b.ext — `type: another description`

### Hold / exclude
- [path] — [why it should remain untouched]

Recommendation: I propose committing [exact current scope] now as `[title]`,
[including an exact additional scope only after approval], and keeping
[remaining scope] for [a follow-up / later decision].

Wait for the user to approve or revise the scope and message. Do not stage or
commit while presenting this proposal.
````
