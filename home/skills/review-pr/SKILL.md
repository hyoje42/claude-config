---
name: review-pr
description: "Review pull requests, branches, commits, or staged diffs with a code-review mindset — and, only when the user explicitly asks, draft a PR title and body that the user can paste into GitHub (or any tool) themselves. Trigger on requests like 'review this PR', 'review my branch against main', 'check whether this is safe to merge', 'review the staged changes', 'review my branch and draft a PR', or 'give me a PR title and body for this branch'. Do not use for simple change summaries, commit-message drafting alone, or general codebase exploration without a concrete change set."
---

# Pull Request Review (and Optional PR Draft)

Primary mode: review a concrete change set and surface actionable issues.
Optimize for correctness, regressions, safety, and missing validation.

Secondary mode, only on explicit user request: after the review, draft a PR
title and body. The skill never pushes the branch, never opens the PR, and
never calls external tools like `gh`. The user performs those steps with
whatever tools they prefer.

Do not draft PR content on your own initiative, even if the review is clean.
Do not spend time on cosmetic nits unless the user explicitly asks for style feedback.

## Usage Examples

Works on **local git refs only**. No remote API, no `gh`, no PR numbers, no URLs. If the change is in a remote PR, check out the branch locally first.

### Slash command: `/review-pr [args]`

- `/review-pr` — current branch vs `main`
- `/review-pr <branch>` — `<branch>` vs `main`
- `/review-pr <target> <base>` — `<target>` vs `<base>`
- `/review-pr --staged` — `git diff --staged`
- Append `draft` to any of the above to also draft a PR title and body (e.g. `/review-pr <branch> draft`)

Parse args flexibly. If any piece is ambiguous, ask before proceeding — do not guess.

### Natural language

Same patterns phrased conversationally:

- "Review my branch against main"
- "Review the staged changes before I commit"
- "Review this branch and draft a PR"

## Quick Start

1. Resolve the review target.
2. Collect the smallest useful diff overview.
3. Inspect risky files in surrounding context.
4. Check tests, docs, and rollout risk.
5. Report findings first. If there are no material findings, say so explicitly.
6. If — and only if — the user then asks for a PR title/body draft, proceed to **Draft PR Content**.

## Resolve The Target

Read [references/target-resolution.md](references/target-resolution.md) when you need exact resolution rules or command patterns.

Supported review modes (all based on local git refs):

- Branch review: current branch or `<target>` against `<base>` — the most common case is comparing the current branch against `main`
- Commit review: single commit or explicit commit range
- Pre-PR review: staged diff or working tree changes

Prefer local refs when they already exist.
Do not assume `origin/main` — the repo's default branch may differ, and a stale assumption wastes the whole review.
Do not fetch by default; fetch only if the needed remote ref is missing and remote data is actually required. Network calls cost time and sometimes require credentials the user has not set up in this session.

## Review Workflow

1. Resolve `{base}` and `{target}` for the requested review mode.
2. Build an overview with diff stats, changed files, commit list, and merge-base-aware diff where appropriate.
3. Prioritize risky areas first: auth, permissions, persistence, migrations, config, caching, concurrency, serialization, external API boundaries, and tests.
4. Read surrounding code for risky hunks instead of reviewing the patch in isolation.
5. Check whether the change introduces missing validation, broken edge cases, unsafe defaults, backward-compatibility issues, or incomplete test coverage.
6. Write the final review using [references/report-format.md](references/report-format.md).

## Review Priorities

Read [references/review-checklist.md](references/review-checklist.md) when the diff is large, risky, or needs a more systematic pass.

Always prioritize:

- correctness and regression risk
- data integrity, migrations, and backward compatibility
- auth, permissions, secrets, and security-sensitive paths
- error handling, retries, timeouts, and cleanup behavior
- test gaps and missing rollout notes

## Output Rules

- Findings come first.
- Order findings by severity and impact.
- Give one issue per bullet.
- Include concrete evidence: file path and line number when available, otherwise the nearest diff hunk or function name.
- Explain why the issue matters and what change would address it.
- If you are uncertain, say what assumption the finding depends on.
- If there are no material findings, state that plainly and mention residual risks or test gaps.

## Draft PR Content (only on explicit user request)

Trigger phrases: "draft the PR", "give me a PR title and body", "prepare PR
content", "write the PR description", etc.
Produce text only. Do not run `git push`, do not open the PR, do not invoke
external CLIs. The user performs every side-effectful step.

### Preconditions

- The review above must already be complete, so the draft is grounded in real
  findings rather than guesses.
- The change set in the review is the intended PR contents. If the review
  target was a commit range or staged diff with no committed branch, ask the
  user which branch will be the PR head — its name often shapes the title.

### Drafting The Title

Keep it short (≤70 chars) and action-oriented. Put detail in the body, not the title.
Match the repo's existing style — inspect `git log --oneline` on the base
branch for conventions (Conventional Commits prefixes, ticket-ID prefixes, etc.).

### Drafting The Body

Start from [references/pr-body-template.md](references/pr-body-template.md) and
fill each section from what the review surfaced:

- **Summary**: what changed and why, in plain language. Do not list every file.
- **Scope**: what is included and what is intentionally excluded, especially if the branch touches adjacent areas.
- **Type Of Change**: check the boxes that apply.
- **Testing**: what was actually verified (tests added, tests run, manual steps). If coverage is thin, say so — do not claim more than is true.
- **Risk And Rollout**: surface anything that came up in review — migrations, feature flags, backward-compatibility, rollout order.
- **Related Issues Or Docs**: include only if the user mentioned them or commit messages reference them. Do not fabricate ticket IDs or links.

Drop sections that genuinely do not apply rather than leaving them empty.

### Output

Present the title and body to the user as one reviewable block they can copy
as-is — for example:

```
Title: <the drafted title>

Body:
---
<the filled template>
---
```

State explicitly that the PR is not opened. The user needs to push the branch
and open the PR themselves using whatever workflow they prefer (browser, their
own CLI, IDE integration).

## When Not To Use

- Simple "what changed?" summaries where no review judgment is needed.
- Drafting only a commit message, with no review and no PR draft.
- General architecture discussion with no concrete diff, branch, commit, or PR target.
- A PR draft request with no preceding review — this skill always reviews first; it does not draft PR content from scratch.
- Anything that requires pushing the branch or opening the PR end-to-end — that is outside this skill's scope and must be done by the user.
