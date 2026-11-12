# Decision Packages

Every stop shows the user one package in their language. A package reports what agents already verified and asks only for decisions agents cannot make.

## How to Present a Stop

The user decides from what is on their screen and has not opened the stage files. Two habits have made users approve a spec they never saw: a package that pointed at `2-spec.md` or named an ID range instead of printing the items, and a question dialog opened with no package printed before it.

- **Write out what is being decided.** Print the spec checklist, the findings, or the proposed changes item by item in the package. A stage-file path or an ID range such as `S1-S6` never stands in for the content; paths are for detail beyond it. Keep the package short by leaving out how you got there, not what the user is approving.
- **Print the package first, then open the dialog.** The package is message text, printed in the same turn before the AskUserQuestion call. The dialog only collects the answer: never ask for a decision on content that message did not print. Before asking, record in `state.md` which stop the loop is waiting at.
- **Make each question readable on its own.** The dialog can cover the text above it, so say in the question what is being decided in a sentence or two, such as the goal and the points that need the user's judgment, instead of naming an ID range.

## Shared Shape

1. **First line:** what is being decided and the orchestrator's recommendation.
2. **What is being decided:** the content listed for that package below, written out.
3. **Verified by agents:** what was checked, by which judge (name the model when known), and the result. Include known weaknesses such as "same-model reviewer" or "no integrity checks".
4. **Needs your decision:** only items agents could not settle, each with a recommendation.
5. **Files:** paths to the stage files for detail.
6. **Ask** with AskUserQuestion after the package text: at most 4 questions, recommended option first.

## Intent Stop ([1])

Ask only outcome-changing unknowns that the repo and context file could not answer. For each, state what was already checked and why it did not settle the question, in the message before the dialog and briefly in the question or its option descriptions.

## Spec Package ([2])

- Goal restated in one sentence.
- Spec checklist, every item written out: its ID, the requirement in one line, and how it is checked. Keep the facts, hypotheses, decisions, and unknowns separate, and write out each decision and unknown the same way.
- Slots: 5-a gates, 5-b judges, done definition, K, and risk tier, each marked as from the context file or a default.
- Mode the run will use. If auto mode was requested and refused, name the failed precondition.
- Resolved roster: runner and model per role, with any model that is assumed rather than known marked as such. Say that it can be changed here in plain words, and show how you read any roster request made in the invocation.
- Slice plan: slices, parallel groups, dependencies.
- Plan-review result: verdict per round, what it caught and fixed, findings applied without re-review after a failed last round, and any open disagreement.
- A context-file draft, if [0] created one: its rules and unverified assumptions in a few lines, plus its path.
- Options: approve, change (say what), stop.

## Final Package ([5-b], in mode)

- Verdict of the judges and the recommendation.
- 5-a results: commands and exit codes.
- 5-b results: deterministic judges, then `verifier` findings with severity.
- Every finding fixed automatically, with the spec item it cited and how it was fixed.
- Spec gaps, spec items the reviewer could not check, and residual risks. Each spec gap needs a decision: add it to the spec, or accept the work as is.
- Reviewer notes, copied as written.
- Integrity-check results: the change list, and any violation that was repaired.
- Proposed changes to `.loop/context.md`, each one written out as it stands in `6-context-proposal.md`.
- Options: accept, send back to the spec (say what is wrong), stop. Accepting does not approve a commit; propose the commit separately.
- A second question in the same AskUserQuestion call: apply the context proposal, apply it with changes, or leave the context file as it is.

## Escalation

- What stopped the loop: the limit hit, the out-of-scope action, the failed integrity check, the spec gap, or the unanswered unknown.
- What was tried, and the evidence (attempt count, gate output excerpt, finding).
- Options to continue, with a recommendation.

## Delivered Report (auto mode)

The same content as the final package, written to `6-report.md` and summarized at the end of the run. The user reviews it after the fact and decides on `6-context-proposal.md` and the commit.
