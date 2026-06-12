# Peer Review Template

Create `.reviews/YYMMDD-{task-slug}/claude-review-YYYY-MM-DD-HHMMSS.md` with the following structure. Drop sections that genuinely do not apply rather than leaving them empty.

Severity levels:

| Severity | Meaning |
|---|---|
| `critical` | Broken behavior, data loss, security issue |
| `major` | Likely bug or significant design problem |
| `minor` | Worthwhile improvement, not blocking |
| `question` | Possibly intentional — needs the author's intent to judge |
| `nit` | Style, naming, cosmetic |

```markdown
# [Task/Topic] - PEER REVIEW

## Review Metadata

- **Reviewer**: claude
- **Date**: YYYY-MM-DD HH:MM KST
- **Target**: [uncommitted changes | commit range `a..b` | file paths]
- **Context provided**: [handoff path, docs, user note — or "none, target only"]
- **Previous rounds**: [user-provided prior review/response files read for an explicit follow-up — or "not read; independent review"]

## Summary

[2-4 sentences: scope reviewed, overall quality, the most important issues]

## Findings

### [severity] Short title

- **Location**: `path/to/file:line`
- **Evidence**: [what was observed — code excerpt, behavior, inconsistency]
- **Why it matters**: [impact / rationale]
- **Suggestion**: [concrete fix or alternative]

### [severity] Next finding

...

## What Looks Good

- [Decisions or implementations the reviewer finds sound — brief]

## Review Limitations

- [What could not be verified, and why — e.g. no intent context beyond the diff; integration test skipped because it would mutate local state]
```

Notes:

- Order findings by severity, most severe first.
- Verification during review must be side-effect-free; every check that mattered but was skipped for that reason belongs in Review Limitations.
- Do not read existing `.reviews/` file contents unless the user explicitly provided them as context or asked for a follow-up round.
- Every finding must point at a concrete location. What you suspect but cannot anchor goes to Review Limitations or a `question` finding.
- The reader is the author agent — possibly a different coding tool. Keep it tool-neutral and self-contained.
