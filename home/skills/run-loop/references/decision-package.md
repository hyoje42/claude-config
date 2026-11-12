# Decision Packages

Every stop shows the user one package in their language. A package reports what agents already verified and asks only for decisions agents cannot make. Keep it short; link the stage files instead of pasting them.

## Shared Shape

1. **First line:** what is being decided and the orchestrator's recommendation.
2. **Verified by agents:** what was checked, by which judge (name the model when known), and the result. Include known weaknesses such as "same-model reviewer" or "no integrity checks".
3. **Needs your decision:** only items agents could not settle, each with options and a recommended one.
4. **Files:** paths to the stage files for detail.
5. **Ask** with AskUserQuestion: at most 4 questions, recommended option first.

## Intent Stop ([1])

Ask only outcome-changing unknowns that the repo and context file could not answer. For each, state what was already checked and why it did not settle the question.

## Spec Package ([2])

- Goal restated in one sentence.
- Spec checklist (IDs and one line each), with the facts, hypotheses, decisions, and unknowns kept separate.
- Slots: 5-a gates, 5-b judges, done definition, K, and risk tier, each marked as from the context file or a default.
- Mode the run will use. If auto mode was requested and refused, name the failed precondition.
- Resolved roster: runner and model per role, with any model that is assumed rather than known marked as such. Say that it can be changed here in plain words, and show how you read any roster request made in the invocation.
- Slice plan: slices, parallel groups, dependencies.
- Plan-review result: verdict per round, what it caught and fixed, findings applied without re-review after a failed last round, and any open disagreement.
- A context-file draft, if [0] created one.
- Options: approve, change (say what), stop.

## Final Package ([5-b], in mode)

- Verdict of the judges and the recommendation.
- 5-a results: commands and exit codes.
- 5-b results: deterministic judges, then `verifier` findings with severity.
- Every finding fixed automatically, with the spec item it cited and how it was fixed.
- Spec gaps, spec items the reviewer could not check, and residual risks. Each spec gap needs a decision: add it to the spec, or accept the work as is.
- Reviewer notes, copied as written.
- Integrity-check results: the change list, and any violation that was repaired.
- Proposed changes to `.loop/context.md`, as written in `6-context-proposal.md`.
- Options: accept, send back to the spec (say what is wrong), stop. Accepting does not approve a commit; propose the commit separately.
- A second question in the same AskUserQuestion call: apply the context proposal, apply it with changes, or leave the context file as it is.

## Escalation

- What stopped the loop: the limit hit, the out-of-scope action, the failed integrity check, the spec gap, or the unanswered unknown.
- What was tried, and the evidence (attempt count, gate output excerpt, finding).
- Options to continue, with a recommendation.

## Delivered Report (auto mode)

The same content as the final package, written to `6-report.md` and summarized at the end of the run. The user reviews it after the fact and decides on `6-context-proposal.md` and the commit.
