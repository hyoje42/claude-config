---
name: review-pr
description: "Review a pull request the way a reviewer would, for someone else's PR or your own branch before you open one: find bugs and regressions, check that the change does what it claims and is scoped and tested well enough to merge, and, when the user asks, draft a PR title and body they can paste themselves. Accepts a GitHub PR number or URL, a local or GitHub branch, a commit range, or staged changes. Never posts, pushes, or opens the PR. Trigger on requests like 'review my branch and draft a PR' or 'give me a PR title and body for this branch'. Do not use for simple change summaries, commit-message drafting alone, or general codebase exploration without a concrete change set."
---

# Pull Request Review (and Optional PR Draft)

Review a change set the way a pull request reviewer would. Requests come in
three kinds:

- Review someone else's PR before it merges.
- Check the user's own branch before they open a PR.
- Draft a PR title and body, only when the user asks.

Every review looks for bugs first: correctness, regressions, data safety,
security, and missing validation. On top of that, judge the change as a PR:
whether it does what its description or commits claim, whether anything
unrelated is mixed in, and whether it is tested well enough to merge.

The skill may read from GitHub but never writes to it: it never posts comments
or reviews, approves, merges, pushes, or opens a PR. The user does those steps
with whatever tools they prefer. Review without checking out other branches, so
the user's working tree and current branch stay as they are.

Do not spend time on cosmetic nits unless the user explicitly asks for style feedback.

## Usage Examples

### Slash command: `/review-pr [args]`

- `/review-pr` — current branch vs the repository's default branch
- `/review-pr <pr-number>` or `/review-pr <pr-url>` — a GitHub PR vs its base branch
- `/review-pr <branch>` — `<branch>` vs the repository's default branch, whether the branch is local or only on GitHub
- `/review-pr <target> <base>` — `<target>` vs `<base>`
- `/review-pr --staged` — `git diff --staged`
- Append `draft` to any of the above to also draft a PR title and body (e.g. `/review-pr <branch> draft`)

Parse args flexibly; they may come mixed with natural language (for example `/review-pr branch-a, focus on the auth changes`). Ask only when an ambiguity would change which changes get reviewed.

### Natural language

Same patterns phrased conversationally:

- "Review PR 123"
- "Review my branch against main before I open a PR"
- "Review the staged changes before I commit"
- "Write a PR description for this branch"

## Resolve The Target

Read [references/target-resolution.md](references/target-resolution.md) for the resolution order, the GitHub and local fallbacks, and command patterns.

Supported review modes:

- PR review: a GitHub PR number or URL, reviewed against the PR's base branch
- Branch review: current branch or `<target>` against `<base>`, whether the branch is local or only on GitHub — when `<base>` is omitted, resolve the repository's default branch
- Commit review: single commit or explicit commit range
- Pre-PR review: staged diff or working tree changes

Use `gh` for GitHub data when it is installed and authenticated; otherwise fall back to local git. If neither can reach the change, say what failed and ask the user to set up `gh` (for example with `gh auth login`).
Prefer local refs when they are current.
Do not assume `origin/main` — the repo's default branch may differ, and a stale assumption wastes the whole review.
Fetch only when the needed ref is missing locally, is stale, or its freshness must be established for a remote review. Network calls cost time and sometimes require credentials the user has not set up in this session.

## Review Workflow

1. Resolve `{base}` and `{target}` for the requested review mode. When a PR exists, read its title and body first; they state what the change claims to do.
2. Build an overview with diff stats, changed files, commit list, and merge-base-aware diff where appropriate.
3. Prioritize risky areas first: auth, permissions, persistence, migrations, config, caching, concurrency, serialization, external API boundaries, and tests.
4. Read surrounding code for risky hunks instead of reviewing the patch in isolation. For a ref that is not checked out, read files with `git show <ref>:<path>`.
5. Check whether the change introduces missing validation, broken edge cases, unsafe defaults, backward-compatibility issues, or incomplete test coverage.
6. Check the change as a PR: does it do what its description or commits claim, is anything unrelated mixed in, and is anything it needs missing (tests, docs, migrations, config)?
7. When the user is checking their own branch before opening a PR, also look for leftovers: debug output, commented-out code, stray TODOs, local-only settings, and related changes still uncommitted that the PR would not include.
8. Write the final review using [references/report-format.md](references/report-format.md).

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
- Write the review output in the user's explicitly requested language; if no language is specified, write it in the user's preferred language.
- Order findings by severity and impact.
- Give one issue per bullet.
- Include concrete evidence: file path and line number when available, otherwise the nearest diff hunk or function name.
- Explain why the issue matters and what change would address it.
- If you are uncertain, say what assumption the finding depends on.
- If there are no material findings, state that plainly and mention residual risks or test gaps.
- For someone else's PR, phrase each finding so the user can paste it as a review comment at that `path:line`.

## Draft PR Content (only on explicit user request)

Trigger phrases: "draft the PR", "give me a PR title and body", "prepare PR
content", "write the PR description", etc.
Produce text only.

### Preconditions

- When the user asks for a review and a draft together (for example `draft` or
  "review this branch and draft a PR"), run the full review first, report the
  findings with merge-blocking issues first, and carry risks that matter for
  merging or rollout into the draft's Risk section.
- When the user asks only for the PR title or body, keep the pass light: read
  the diff, the commit messages, and enough surrounding code to describe the
  change accurately, and skip the findings report. If you notice a
  merge-blocking problem along the way, mention it in one line after the draft.
- Do not run builds or tests on your own for a draft. If the user or the
  repository's PR template or contribution checklist calls for checks that were
  not run, list them after presenting the draft and ask the user whether to run
  them. Report only what was actually run.
- The resolved change set is the intended PR contents. If the target was a
  commit range or staged diff with no committed branch, ask the user which
  branch will be the PR head — its name often shapes the title.

### Drafting The Title

Keep it short (≤70 chars) and action-oriented. Put detail in the body, not the title.
Match the repo's existing style — inspect `git log --oneline` on the base
branch for conventions (Conventional Commits prefixes, ticket-ID prefixes, etc.).

### Drafting The Body

If the repository has its own PR template or contribution checklist (for
example `.github/PULL_REQUEST_TEMPLATE.md`, `.github/pull_request_template.md`,
or `CONTRIBUTING.md`), follow its structure and check only the items that were
actually done. Otherwise start from
[references/pr-body-template.md](references/pr-body-template.md). Either way,
keep the body short and plain:

- Write the PR title and body in the user's explicitly requested language; if no language is specified, write them in the user's preferred language.
- **Summary**: what changed and why, in a few plain sentences.
- **Changed files**: group the changed files and give each file or group a one-line reason.
- **Testing**: what was actually verified (tests added, tests run, manual steps). If coverage is thin, say so — do not claim more than is true.
- **Risk**: anything from the review that affects merging or rollout, such as migrations, feature flags, backward compatibility, or rollout order.
- Mention related issues or docs only if the user mentioned them or commit messages reference them. Do not fabricate ticket IDs or links.

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

End by noting that the PR has not been opened; the user pushes the branch and
opens it with their own workflow.

## When Not To Use

- Simple "what changed?" summaries where no review judgment is needed.
- Drafting only a commit message, with no review and no PR draft.
- General architecture discussion with no concrete diff, branch, commit, or PR target.
