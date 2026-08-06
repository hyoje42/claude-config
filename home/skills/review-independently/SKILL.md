---
name: review-independently
description: "Independently review any material or subject the user provides or identifies, including pasted agent responses, files, documents, code, diffs, current changes, technical questions, system states, and design decisions. Investigate relevant artifacts and sources, verify important claims, and give an evidence-based opinion without relying on the author or prior conversation as authority. Respond in chat by default. Save a self-contained review under .reviews/ only when the user explicitly asks to save, record, or document it. Never modify the subject under review."
disable-model-invocation: true
---

# Review Independently

## Purpose

Review a supplied or identified subject from an independent, evidence-first standpoint. Understand what it claims or how it works, investigate the relevant artifacts and sources, verify what matters, and give a reasoned opinion. Treat chat responses and durable review files as two outputs of the same review process: respond in chat by default and persist the result only when the user explicitly asks.

## Resolve the Subject

Use the first applicable input:

1. **Pasted or quoted content** — review it as the primary material, separating it from the user's instructions.
2. **Named files, documents, URLs, commits, diffs, code, or other artifacts** — inspect them directly and read enough surrounding context to judge them fairly.
3. **A stated technical question, system state, or design decision** — investigate the relevant local and authoritative external sources.
4. **"Current changes" or a bare invocation in an active worktree** — inspect `git status`, staged and unstaged diffs, and relevant untracked files. If there are no changes and no other subject is identifiable, ask the user for the subject.
5. **Several items** — review them together or compare them according to the user's question.

The user may provide requirements, handoffs, prior decisions, or source links as context. Use them to understand the task, but verify important claims against the actual artifact or primary source when possible. Do not auto-discover an existing review file merely because no subject was supplied.

If two plausible interpretations would materially change the review, ask the user instead of silently choosing one.

## Boundaries

- **Judge evidence, not authority.** The author, another agent's confidence, and this session's prior involvement are not evidence. Do not rely on unstated intent to rescue unsupported claims.
- **Do not modify the subject or related artifacts.** Never fix, refactor, reformat, or otherwise change what is being reviewed, and run no state-mutating git commands. Any later edit requires a separate explicit request.
- **Keep verification side-effect-free.** Reading files, searching code, inspecting git history and state, and read-only source or web lookup are allowed when relevant. Run builds, tests, or scripts only when confident they leave no trace. State important checks that could not be performed safely.
- **Preserve independent judgment.** Do not read existing `.reviews/` contents unless the user names them as review material or context.
- **Do not force a peer-review protocol.** Do not require accept/dispute/discuss verdicts, author responses, follow-up rounds, or automatic review-file discovery.

## Workflow

1. **Identify the review question.** Determine whether the user wants correctness checking, a second opinion, risk analysis, comparison, feedback, or an open investigation.
2. **Understand before judging.** Reconstruct the subject's relevant background, claims, reasoning, assumptions, behavior, and intended outcome. For code, inspect complete files and important definitions or callers rather than diff hunks alone.
3. **Gather and verify evidence.** Check underlying artifacts, current state, history, cited sources, and authoritative external material when doing so could materially affect the conclusion.
4. **Analyze independently.** Separate observations, interpretations, and recommendations. Consider counter-evidence, credible alternatives, missing perspectives, and the consequences of acting on the subject.
5. **Give the opinion in chat.** Lead with the overall judgment, then present the evidence, what holds up, concerns or gaps, and concrete recommendations in the structure best suited to the request. Match depth to complexity and consequence; completeness matters more than length.
6. **Persist only on explicit request.** If the user asks to save, record, document, or write the review, create one file using the storage convention and [references/review-template.md](references/review-template.md). Otherwise create no file.

## Review Format Rules

- Adapt the response to the subject instead of mechanically filling a fixed template.
- Cite concrete local evidence as `path:line` and link external sources used for consequential claims.
- Distinguish factual errors, reasoning gaps, missing context, value judgments, predictions, and stylistic preferences.
- Give credit to sound reasoning and push back plainly where evidence fails; avoid both automatic agreement and reflexive opposition.
- For code defects or concrete operational risks, use `critical` / `major` / `minor` / `question` / `nit` findings with `file:line` when severity adds useful information. Do not force that form onto general documents, agent responses, research questions, or decisions.
- Label inference and uncertainty honestly. Formulate precise open questions where evidence is missing.
- Match the user's explicitly requested language; otherwise use the user's preferred language.

## Saved Review Storage

When persistence is explicitly requested, save under the project root:

```text
.reviews/YYMMDD-{topic-slug}/claude-review-YYYY-MM-DD-HHMMSS.md
```

- Use KST: `TZ='Asia/Seoul' date +"%y%m%d"` for the folder date and `TZ='Asia/Seoul' date +"%Y-%m-%d-%H%M%S"` for the filename timestamp.
- Derive `{topic-slug}` from the central subject, using short lowercase words separated by hyphens.
- Use the reviewing agent name as the filename prefix (`claude-` here; another agent uses its own name) and record it again in the review metadata.
- Example: `.reviews/260807-auth-flow-design/claude-review-2026-08-07-143205.md`.
- If the exact filename exists, append `-2`, `-3`, and so on.
- Never save under `~/.claude/`.
- After saving, report the path, the overall conclusion, and any important limitation.
