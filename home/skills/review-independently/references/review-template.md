# Saved Independent Review Template

Use this template only when the user explicitly asks to save, record, document, or write the review. Create:

```text
.reviews/YYMMDD-{topic-slug}/claude-review-YYYY-MM-DD-HHMMSS.md
```

Translate headings and prose into the user's explicitly requested language; otherwise use the user's preferred language. Keep paths, identifiers, commands, conventional severity labels, and source URLs unchanged.

```markdown
# [Subject] — INDEPENDENT REVIEW

## Review Metadata

- **Reviewing agent**: claude
- **Created**: YYYY-MM-DD HH:MM KST
- **Subject**: [material, work product, question, state, or decision reviewed]
- **Review request**: [what the user asked the reviewer to determine]
- **Inputs**: [pasted response, paths, URLs, commit or diff range, or other identifiers]

## Background and Scope

[Reconstruct the context needed by a reader who has not seen the originating conversation. State what was and was not reviewed.]

## Evidence Reviewed

- [Local artifact and `path:line`, git evidence, primary source, or authoritative URL]

## Analysis

[Connect the evidence to the judgment. Separate direct observations, interpretations, counter-evidence, alternatives, and recommendations.]

## Conclusion

[State what the evidence supports and the most important practical implication.]

## Limitations and Open Questions

- [Skipped verification, unavailable source, uncertainty, assumption, or unresolved question; state "none identified" when appropriate]
```

For code defects or concrete operational risks, use this optional finding form when severity is useful:

```markdown
### [critical|major|minor|question|nit] Short title

- **Location**: `path/to/file:line`
- **Evidence**: [what was observed]
- **Impact**: [why it matters]
- **Recommendation**: [specific action, not applied]
```

Do not force severity findings onto general documents, pasted agent responses, research questions, system assessments, or design decisions.

Before saving, verify that a capable reader with no access to the conversation can identify the subject, background, scope, evidence, reasoning, conclusion, reviewing agent, limitations, and open questions.
