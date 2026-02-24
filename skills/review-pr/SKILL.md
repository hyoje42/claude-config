---
name: review-pr
description: "Use this skill when the user wants to review a Pull Request. Trigger on requests to review PRs, analyze code changes, provide code review comments, check pull request quality, or evaluate merged code. This includes reviewing PRs by branch name, comparing branches, or analyzing changes between commits (e.g., \"review the feature-xyz branch\", \"check changes from main\", \"review PR #123\" if branch is known). Use when user asks for code review, PR analysis, change assessment, or wants feedback on proposed changes. Do NOT use for general code analysis, file reading, or codebase exploration not related to a specific PR/branch."
---

# Pull Request Review

## Review Workflow

1. **Ask for target**: Which PR/branch to review
2. **Fetch changes**: `git fetch origin`
3. **View diff**: `git diff origin/main...origin/feature-branch`
4. **Check files**: `git diff --name-only origin/main...origin/feature-branch`
5. **Review commits**: `git log origin/main..origin/feature-branch --oneline`
6. **Provide feedback**: Use the review template below

## Git Commands Quick Reference

| Task | Command |
|------|---------|
| View diff | `git diff base...target` |
| Changed files | `git diff --name-only base...target` |
| Diff stats | `git diff --stat base...target` |
| Commit history | `git log base..target --oneline` |
| Specific file | `git diff base...target -- path/to/file` |

## Review Checklist

First, check for PR template in the workspace:

1. Look for `.github/PULL_REQUEST_TEMPLATE.md` or `.github/pull_request_template.md` in the workspace root
2. If not found, use the skill's [pull_request_template.md](templates/pull_request_template.md)

Review the PR against the template format:

- **Description**: Is the change clearly described?
- **Type**: Does the change type (New features/Bug Fix/Refactoring/etc.) match the actual changes?
- **Status**: Is the PR marked as COMPLETED?
- **Code quality**: Bugs, logic errors, edge cases
- **Testing**: Are tests added/updated?
- **Documentation**: Is the documentation updated?
- **Related issues**: Are related issues linked?
