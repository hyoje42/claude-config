---
name: load-review
description: "Use this skill ONLY when the user explicitly invokes it — /load-review or naming \"load-review\" — to have this agent respond to a peer review of its work (e.g. /load-review .reviews/YYMMDD-task/codex-review-xxx.md). A .reviews/ path alone is NOT a trigger: if the user asks to show, read, or summarize a review file without asking for a response to it, read the file normally without this skill. Invoked without a path, it auto-discovers candidates under .reviews/. Best run in the session that did the work; a fresh session or a different agent also works — verdicts are then grounded in the reviewed artifact, relevant source material, git state when applicable, and any context the user provides. Produces evidence-based verdicts (accept/dispute/discuss) and a response file under .reviews/ — opinions only: it never edits code, documents, or other reviewed artifacts; fixes happen later, outside this skill, only on the user's explicit instruction. Do NOT use to write a fresh review (use write-review)."
---

# Load Review

## Purpose

Bring a peer review back to an agent that answers for the work: re-verify every finding against the reviewed artifact and relevant evidence, agree or push back with evidence, and record the verdicts in a response file. **Opinions only** — this skill changes nothing; whether and when to apply any fix is the user's later, explicit call.

## Role Boundaries

- **The response file under `.reviews/` is the only thing this skill creates or modifies.** Never edit the code, documents, or other artifacts under discussion — not even findings you accept, not even trivial ones. Fixes happen after the skill ends, only when the user explicitly instructs (directly or via another skill).
- **Side-effect-free verification only.** Re-reading files, grep, `git diff` / `git log`, and read-only web/source lookup are fine when relevant and allowed by the environment. Run builds, tests, or scripts only when confident they leave no trace. A finding that cannot be verified without side effects becomes 🤔 discuss, with the skipped check named in the report.
- **The reviewed artifact and its source material are the ground truth** — not your memory of them, and not the reviewer's authority.

## Workflow

1. **Resolve the review file path** from args:
   - Absolute path → use as-is; relative path → resolve from workspace root; `@` file reference → already converted to absolute path
   - **No path given** → discover candidates with `ls -t .reviews/*/*-review-*.md 2>/dev/null`:
     - none → see Error Handling
     - exactly one → load it, stating which file you are using
     - several → propose the most recent review that has no newer `*-response-*.md` in its folder (i.e. not yet responded to), list the other candidates briefly, and confirm with the user before proceeding
2. **Establish your standpoint** — both are supported:
   - **You are the session that did the work** (ideal): reflect with full context — you know the intent, requirements, and tradeoffs behind each choice.
   - **You are a different agent or a fresh session**: say so in your report. Ground yourself first: read the review's Target metadata, inspect the current target (`git diff` / `git log` for code changes, target files for documents, or the cited artifact/source material for other work), and absorb any context the user provided (a handoff file, a one-line task summary, requirements, or source links). Then answer for the work based on what the artifact and evidence actually show.
3. **Evaluate each finding independently**:
   - Re-read the cited location and surrounding context; verify the claim within the side-effect-free limit above
   - For factual or external claims in documents, reports, plans, or analyses, check the cited source material and, when useful and allowed, search authoritative web sources; cite what you used
   - Give each finding a verdict — ✅ accept / ❌ dispute / 🤔 discuss — per the rules below
   - Answer `question` findings: from session knowledge if you are the author, from the artifact, evidence, or the user otherwise
4. **Report to the user** using the response template below: per-finding verdicts with reasoning, and for each accepted item the fix you would make — without making it.
5. **Record the response file** at `.reviews/{same-task-folder}/claude-response-YYYY-MM-DD-HHMMSS.md` following [references/response-template.md](references/response-template.md), so the reviewer can run a follow-up round against your verdicts.

The skill ends there. If the user then explicitly asks to apply some or all accepted fixes, that is regular work outside this skill.

## Verdict Rules

- **Reviewer authority is not evidence.** Accept a finding only after confirming it yourself at the cited location. What you cannot confirm is a dispute or a discussion item — never a polite accept. Blanket agreement defeats the purpose of this skill.
- **Defensiveness is the symmetric failure.** Do not protect the work because it is "yours"; when the evidence stands, accept plainly.
- ✅ **Accept** — confirmed against the artifact and evidence → describe the exact fix you would make (do not make it)
- ❌ **Dispute** — counter-evidence found → cite it concretely (`file:line`, observed behavior, source link, or the requirement it serves)
- 🤔 **Discuss** — hinges on intent or requirements only the user knows, genuinely uncertain, or unverifiable without side effects → formulate the precise question or name the missing check

## Response Template

```markdown
## 📋 Peer Review Processed

**Review**: [file path] (by [reviewer])
**Standpoint**: [original author session | different agent — grounded in the artifact/git state + provided context]

### Verdicts — [n] findings: [a] accept / [d] dispute / [k] discuss

#### ✅ [severity] [finding title]
[why it is correct] → **Proposed fix (not applied)**: [what would change]

#### ❌ [severity] [finding title]
[counter-evidence, with location]

#### 🤔 [severity] [finding title]
[the open question for the user, or the check skipped for side-effect risk]

---

**No changes were made.** Say explicitly which accepted fixes to apply, if any — that happens outside this skill.
```

## Error Handling

- **No reviews found / file not found**: report it and suggest checking `ls -lt .reviews/*/ 2>/dev/null`, or running `write-review` from the reviewer agent first.
- **Not a review file** (no Findings section): warn that it does not look like a peer review, summarize what is there, and ask whether to proceed.
- **Target changed since the review**: if a cited location no longer matches, note the staleness in that verdict and judge against the current artifact and evidence.
