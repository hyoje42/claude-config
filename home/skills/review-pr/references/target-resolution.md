# Target Resolution

Resolve the smallest concrete review target that matches the user's request.

This skill works on local git refs only. It does not call GitHub APIs, does not use `gh`, and cannot resolve PR numbers or PR URLs. If the change lives in a remote PR, the user must check out the branch locally first.

## Review Modes

### Branch Review

Use this when the user gives a branch name or says "review this branch".

- Explicit pair: review `<target>` against `<base>`.
- Current branch: if the current branch is not the default branch, review it against the default branch.
- Local-only branch: compare the local branch directly; do not require a remote.

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

When the user does not specify a base, resolve it in this order:

1. The current branch's upstream target, if it is clearly configured
2. The repository default branch from `refs/remotes/origin/HEAD`, if available
3. An existing local branch named `main`, `master`, or `develop`

If more than one reasonable base exists and the choice affects the review, ask the user instead of guessing.

## Local Vs Remote Refs

Prefer refs that already exist locally.

- Check local refs first: `git rev-parse --verify <ref>`
- Use `origin/<branch>` only when that remote ref is needed and present
- Fetch only when missing remote data is necessary to answer the request

`git fetch origin` is not a default first step.

## Minimum Review Context

Once the target is resolved, gather:

- diff stats
- changed file list
- commit list when the review spans multiple commits
- surrounding code for risky hunks

Do not read every changed file end-to-end if the overview already shows where the real risk is.
