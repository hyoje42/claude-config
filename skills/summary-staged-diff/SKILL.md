---
name: summary-staged-diff
description: "Analyze staged git changes and produce a structured summary of what was modified, added, or removed — like drafting a PR description. Use this skill whenever the user asks to summarize their changes, explain what they did, review staged files, describe their work for others, draft a PR summary, or wants a changelog-style overview of their current modifications. Also trigger on: 'what did I change', 'explain my diff', 'summarize my work', 'show what I've done'."
---

# Summary Staged Diff

Analyze staged git changes and produce a clear, structured summary that explains what was changed and why it matters — as if writing a PR description for a teammate.

## When to use

- User has staged files (`git add`) and wants a summary before committing
- User wants to explain their work to others
- User wants to review what they've done in a structured format

## Workflow

1. **Check staged files exist**:
   - Run `git diff --staged --stat` to see staged file list and change statistics
   - If nothing is staged, inform the user and suggest running `git add` first
2. **Collect diff details**:
   - Run `git diff --staged --find-renames` for full diff content with rename detection
   - For large diffs, read individual files to understand context
3. **Analyze and categorize**: Group changes by feature or purpose (not by file)
4. **Highlight key changes**: Extract the most important code-level changes per file
5. **Output**: Use the response format below

## Response format

```markdown
## Summary

One-liner: what this changeset does, as if answering "what did you work on?"

## Changes

### [Category] (feat / fix / refactor / chore / etc.)

Description of what changed and why. Include motivation and context.

Key changes:
- Specific description of a notable code change (e.g., "added validation logic for X")
- Another notable change

Related files:
- [file.ext](path/to/file.ext) — what changed in this file

<details>
<summary>Code highlights</summary>

Show the most important diff snippets (added/removed lines) that illustrate the change.
Use diff code blocks:

\`\`\`diff
- old line
+ new line
\`\`\`

</details>

### [Next category]

...

## Files changed

| File | Status | Lines | Description |
|------|--------|-------|-------------|
| [file.ext](path/to/file.ext) | added / modified / deleted / renamed | +N / -M | brief description |

## Notes

- Any caveats, follow-up items, or things to watch out for
- Migration steps if applicable
- Breaking changes if any
```

## Guidelines

- Group changes by feature or purpose, not by file
- Write descriptions that a teammate unfamiliar with the code can understand
- For renamed/moved files, use `--find-renames` to detect them properly
- Always include code highlights for non-trivial changes — show the actual diff snippets
- Include per-file line count changes in the files table
- Add a Notes section only when there are meaningful caveats, follow-ups, or breaking changes
- Binary files: show filename and size only

## Keywords

summarize changes, what did I change, explain my diff, staged summary, PR description, describe my work, review my changes, changelog, diff summary
