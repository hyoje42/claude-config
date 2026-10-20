# Target Resolution

Resolve the smallest concrete review target that matches the user's request.

## GitHub Access

Use `gh` only to read, with these subcommands: `gh auth status`, `gh repo view`,
`gh pr view`, `gh pr diff`, `gh pr list`, and `gh pr checks`. Anything that
writes to GitHub or changes the local checkout is the user's step.

`gh` is usable when `gh auth status` succeeds and the repository has a GitHub
remote. When it is not usable, fall back to local git as described below. If
neither `gh` nor local git can reach the change, say what failed and ask the
user to set up `gh` (for example with `gh auth login`) or to check out the
branch.

When the repository has several remotes (for example `origin` and `upstream`),
use the remote where the branch or PR actually exists. `gh` picks one remote on
its own when there are several, and it may not be the one you mean, so pass
`--repo <host>/<owner>/<repo>` for that remote (a PR URL already names it).
Do not run `gh repo set-default`; it writes to the local git config. If the
branch or PR exists on more than one remote and they differ, ask which one to
review.

## Review Modes

### PR Review

Use this when the user gives a PR number or URL, or when a branch turns out to
have an open PR.

With `gh`:

```bash
gh pr view <N> --json number,title,body,url,baseRefName,headRefName,headRefOid,isCrossRepository
gh pr diff <N>
gh pr checks <N>
```

Read the title and body first; they state what the change claims to do. Review
against the PR's base branch.

To compare the PR and read surrounding code without checking out, fetch its
base branch and head from the PR's base repository. An existing remote-tracking
base may be stale. Each fetch overwrites `FETCH_HEAD`, so run
`git rev-parse FETCH_HEAD` right after each successful fetch and write the
printed SHA into later commands. Shell variables do not survive between
separate commands, and an empty SHA would turn `git show <sha>:<path>` into
`git show :<path>`, which reads the local index instead of the PR.

```bash
git fetch <remote> refs/heads/<base>
git rev-parse FETCH_HEAD        # record the printed SHA as <base-sha>
git fetch <remote> pull/<N>/head
git rev-parse FETCH_HEAD        # record the printed SHA as <head-sha>
git show <head-sha>:<path>
git diff <base-sha>...<head-sha>
```

Here `<base>` is `baseRefName`. If either fetch fails, stop this sequence and
report the limitation instead of comparing stale refs or a previous `FETCH_HEAD`.
`pull/<N>/head` exists on GitHub remotes, including PRs opened from forks.
Without `gh`, these fetches still give the diff and files but not the PR title
or body; say so in the review. The head ref alone does not identify the PR's
base branch; if it is not otherwise verified, ask the user for it before
fetching the base and comparing.

### Branch Review

Use this when the user gives a branch name or says "review this branch".

- Explicit pair: review `<target>` against `<base>`.
- Current branch: if the current branch is not the default branch, review it
  against the default branch. If it is the default branch, review the commits
  not yet on its upstream (`git log @{upstream}..HEAD`) plus working-tree
  changes; if there is no upstream or nothing to review, say so and ask for a
  target.
- Local branch: compare it directly; a remote is not required. If `gh` is
  usable, look for an open PR with `gh pr list --head <branch>` and read its
  title and body as the change's stated intent.
- Branch only on GitHub: if `gh pr list --head <branch>` finds a PR, continue as
  a PR review. Otherwise fetch that branch (`git fetch <remote> refs/heads/<branch>`),
  then immediately capture `git rev-parse FETCH_HEAD` after the fetch succeeds
  and use that SHA as `<target>`. Do not assume `<remote>/<branch>` was created
  or updated: single-branch clones and restricted fetch mappings may leave it
  absent or stale.
- Local and GitHub copies differ: compare the local branch with the PR's
  `headRefOid` (or `<remote>/<branch>` when `gh` is not usable, noting that it
  is only as fresh as the last fetch). If the local branch is ahead, it holds
  unpushed work: review the local branch and say the PR does not include those
  commits yet. If it is behind, review the GitHub version and say the local
  copy is stale. If they diverged, ask which one to review.

Use a PR-style diff for branch review:

```bash
git diff <base>...<target>
git diff --stat <base>...<target>
git diff --name-only <base>...<target>
git log --oneline <base>..<target>
```

### Commit Review

Use this when the user names a commit SHA or range.

- Single commit:

```bash
git show --stat <commit>
git diff <commit>^!
```

- Explicit range:

```bash
git diff <from>..<to>
git log --oneline <from>..<to>
```

Use the exact range the user asked for. Do not silently convert an explicit commit range into branch-style comparison semantics.

### Pre-PR Review

Use this when the user wants feedback on local changes that are not yet in a PR.

- Staged changes:

```bash
git diff --staged --stat
git diff --staged
```

- Working tree changes:

```bash
git diff --stat
git diff
```

## Choosing The Base

For a PR, the base is the PR's base branch (`baseRefName`).

Otherwise, when the user does not specify a base, resolve it in this order:

1. The default branch advertised by the target branch's remote, using
   `refs/remotes/<remote>/HEAD` when that symbolic ref exists
2. Another unambiguous remote default branch, such as
   `refs/remotes/origin/HEAD`
3. An existing local branch named `main`, `master`, or `develop`

If more than one reasonable base exists and the choice affects the review, ask the user instead of guessing.

The target branch's upstream tracking ref is **not** its review base. For
example, if `feature/login` tracks `origin/feature/login`, do not compare those
two refs; resolve the repository's default branch instead.

## Local Vs Remote Refs

Prefer local refs when they are current.

- Check local refs first: `git rev-parse --verify <ref>`
- Use `<remote>/<branch>` only when that remote ref is needed and present
- Fetch only when the needed ref is missing locally, is stale, or its freshness
  must be established for a remote review

A bare `git fetch <remote>` is not a default first step; fetch the single ref
you need. A fetch adds objects and updates `FETCH_HEAD` or remote-tracking refs
but leaves local branches and the working tree alone; mention it in the review.

## Minimum Review Context

Once the target is resolved, gather:

- PR title and body, when a PR exists
- diff stats
- changed file list
- commit list when the review spans multiple commits
- surrounding code for risky hunks
