# Review Response Template

After the verdicts are settled, record the response at `.reviews/{same-task-folder}/claude-response-YYYY-MM-DD-HHMMSS.md`.

- Timestamp — KST: `TZ='Asia/Seoul' date +"%Y-%m-%d-%H%M%S"`. If the exact filename already exists, append `-2`, `-3`, ...
- The `claude-` prefix identifies the responding agent (a response from another agent would be `codex-response-*.md`, etc.).

This file closes the loop: when the user starts a follow-up round, they provide this response (with the original review) to the reviewer's `write-review`, which then follows up on disputed and discussed items — reviewers do not read `.reviews/` files on their own.

```markdown
# [Task/Topic] - REVIEW RESPONSE

## Response Metadata

- **Author**: claude
- **Date**: YYYY-MM-DD HH:MM KST
- **Review file**: [path of the review this responds to]
- **Standpoint**: [original author session | different agent grounded in the artifact/git state + provided context]

## Verdicts

### ✅ Accepted

- **[finding title]** ([severity]) — [why accepted] → **proposed fix (not applied)**: [what would change]

### ❌ Disputed

- **[finding title]** ([severity]) — [counter-evidence, with location]

### 🤔 To Discuss

- **[finding title]** ([severity]) — [open question, skipped check, or the user's decision if one was made]

## Notes for the Reviewer

- [anything useful for a follow-up round — or drop this section]
```

Notes:

- Keep finding titles identical to the review file so rounds stay traceable.
- This response records opinions only — `read-review` applies no fixes, so the work under review is unchanged at response time. Fixes the user orders afterwards will show up in the next round's target.
- Write tool-neutral: the reviewer may be a different coding agent.
