# Report Format

Default to a code-review response, not a PR summary.

## Structure

### Findings

List the actionable issues first, ordered by severity.

Use one bullet per finding:

```markdown
- High — `path/to/file.ext:123`: The change does X, which can cause Y when Z happens. Suggestion: do A instead.
```

Rules:

- Include file path and line number when available
- If an exact line is not practical, cite the function, block, or nearest hunk
- Explain the impact, not just the symptom
- Suggest the smallest fix that would address the issue

### Open Questions Or Assumptions

Include this section only when a conclusion depends on missing context.

```markdown
Open questions / assumptions:
- I assumed the migration runs before old workers are drained. If that is guaranteed, the compatibility risk is lower.
```

### Change Summary

Optional. Keep it short. Use this only after the findings.

### Verdict

Close with one of:

- `Approve`
- `Comment`
- `Request changes`

Add one sentence explaining why.

## No-Finding Case

If no material issues are found, say so explicitly:

```markdown
No material findings.

Residual risk:
- The change is lightly tested around retry behavior.
```

Do not pad the response with low-value praise or style notes just to avoid an empty findings list.
