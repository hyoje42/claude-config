---
name: write-review
description: "Write a peer-review document for work produced by another agent or session (code changes, commits, or documents). This skill reads the target and writes one review file under .reviews/; it never fixes, edits, or otherwise modifies anything. It must not read other .reviews files unless the user explicitly names them as context or asks for a follow-up review. Default target: the uncommitted changes (git diff); also accepts a commit range, file paths, or a document path, plus optional context files such as a handoff. The author agent processes the resulting file with the read-review skill."
disable-model-invocation: true
---

# Write Review

## Purpose

Review work produced by another agent with fresh eyes — code changes or documents — and write the findings to a standard review file that the author agent can process with the `read-review` skill. The review file is the entire output of this skill.

## Role Boundaries

- **The review file under `.reviews/` is the only thing this skill creates or modifies.** Never fix, refactor, or format the work under review — not even a trivial typo — and run no state-mutating git commands. Whether anything changes is the author's call, made after `read-review`, on the user's explicit instruction.
- **Review isolation by default.** Do not open, read, summarize, or use the contents of any existing `.reviews/*/*-review-*.md` or `.reviews/*/*-response-*.md` file unless the user explicitly provides that file as context or asks for a follow-up round. This prevents parallel reviewers from seeing each other's conclusions.
- **Side-effect-free verification only.** Reading files, grep, `git diff` / `git log`, and read-only web/source lookup are fine when relevant and allowed by the environment. Run builds, tests, or scripts only when confident they leave no trace (no worktree writes, no network calls, no installs, no DB writes). If a check genuinely matters but carries side-effect risk, do not run it — record it under Review Limitations and repeat it in your final report.
- You did not do this work, and that is the point: review what is actually there, free of the author's assumptions. Where intent cannot be known from the artifacts, raise a `question` finding instead of asserting a defect.
- This skill is meant for an agent other than the author. If the user invokes it on work done in this same session, point out that the fresh-eyes value is lost and confirm before proceeding.

## Determining the Review Target

Parse the request in this order:

1. **No target / "current changes"** → uncommitted work: `git status`, `git diff`, `git diff --staged`, plus untracked files that belong to the work.
2. **Commit range** (e.g. `HEAD~3..HEAD`, `abc123..def456`) → `git diff <range>` and `git log <range>`.
3. **File or document paths** → review those files as they are (typical for documents or analysis writeups).

The user may also pass **context files** — e.g. a handoff (`.handoffs/...`) or a design doc "to refer to". Use them to understand intent and requirements; do not review a context file itself unless asked to.

If the target is ambiguous, or the working tree is clean and no target was given, ask the user instead of guessing.

## Storage Convention

Reviews live in the **project root's** `.reviews/` directory, shared across coding agents (parallel to `.handoffs/`):

```
.reviews/YYMMDD-{task-slug}/claude-review-YYYY-MM-DD-HHMMSS.md
```

- `YYMMDD` (folder date) — KST: `TZ='Asia/Seoul' date +"%y%m%d"`
- `{task-slug}` — task name, lowercase, hyphens for spaces. Reuse the slug of a related `.handoffs/*-{task-slug}` folder if one exists. Reuse an existing `.reviews` task folder only when the user explicitly identifies this as a follow-up round or provides a prior review/response file as context.
- `claude-` filename prefix identifies the reviewer, so reviews from other agents (e.g. `codex-review-*.md`) can share the same task folder
- Timestamp — KST: `TZ='Asia/Seoul' date +"%Y-%m-%d-%H%M%S"`. If the exact filename already exists, append `-2`, `-3`, ...
- **NEVER** save under `~/.claude/` (global folder).

## Workflow

1. **Determine the target** (above) and read any provided context files.
2. **Preserve reviewer independence**: unless the user explicitly supplied prior review/response files as context, do not read any existing `.reviews/` file contents. If this is an explicit follow-up round, read only the user-named prior files.
3. **Review independently**: read the actual files, not just diff hunks — open surrounding code to judge how the change fits. For code: correctness, edge cases, error handling, consistency with codebase conventions, design soundness. For documents: factual accuracy against the code/data they describe, internal consistency, completeness — check cited sources for factual or external claims and, when useful and allowed, verify against authoritative web sources, citing what you used. Verify claims yourself within the side-effect-free limit above (grep callers, read the definition, run a read-only check) instead of trusting them.
4. **Write the review file** following [references/review-template.md](references/review-template.md). Every finding needs a location, evidence, and a concrete suggestion. Record skipped or impossible checks under Review Limitations.
5. **Report back**: the file path, a short summary with finding counts by severity, any check that mattered but was skipped for side-effect risk, and instruct the user to run `/read-review <path>` in the author agent's session.

## Review Principles

- **Evidence over opinion** — cite `file:line` and what you observed. A claim you cannot anchor to the artifact is not a finding.
- **Calibrate severity** (levels defined in the template); when intent is unknown, prefer `question` over asserting a defect.
- **Note what is done well** — it calibrates the author's reflection and separates deliberate choices you agree with from issues you missed.
- **Write tool-neutral and self-contained** — the reader is another coding agent, possibly a different tool, that has not seen this conversation.
- **Match the user's language** — write the review in the user's explicitly requested language; if no language is specified, write it in the user's preferred language.
