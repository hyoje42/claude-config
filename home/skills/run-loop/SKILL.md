---
name: run-loop
description: "Run a non-trivial task through the agentic workflow playbook's 0-6 loop as a pure orchestrator: subagents do the work, independent agents verify it, and the user only receives agent-verified packages to make the key decisions. Modes: in (default) and on."
disable-model-invocation: true
argument-hint: "[--auto] <goal in one sentence> | resume [slug]"
---

# Run Loop

## Purpose

Orchestrate a task through the loop from the Agentic Workflow Playbook (https://github.com/jha0313/agentic-workflow-playbook): `[0] context → [1] intent → [2] spec → [3] decompose → [4] implement → [5-a] gates → [5-b] external verification → [6] improve`, feeding lessons back into the context file for the next loop.

You own the flow. Subagents do the work. Independent judges verify it. Spend the user's attention only on decisions agents cannot make, and show the user material only after agents have checked it.

**Invariant: no worker grades its own output.** The 5-b judge never sees a worker's claims about its own correctness, and is never a fork of this conversation. An instruction such as "do not modify any file" is not a control, so every worker run is followed by an [integrity check](#integrity-checks).

## Invocation

Parse `$ARGUMENTS`:

- `--auto` selects auto mode; otherwise use in mode.
- Words that ask for a roster setting, such as "verify with a different model" or "run the verifier as a separate CLI process", set the [roster](#roster) for this run. There is no key-value syntax: map the request to a role and field yourself, and show your reading in the spec package so the user can correct it.
- `resume [slug]` resumes an unfinished loop. See [Resume](#resume).
- The remaining text is the goal. If it is empty, ask for a one-line goal.

Check fit before starting. If the task would take a person only minutes, will be done once and thrown away, has no possible external judge, or is judged by taste rather than by a checkable standard, say so in one or two sentences and recommend doing it directly. Continue only if the user insists.

## Modes

The playbook's automation ladder: in mode is "human in the loop", auto mode is "human on the loop" (the human owns only context and the spec).

| | in (default) | auto |
|---|---|---|
| Planned human stops | [2] spec package; [5-b] final package | [2] spec package |
| 5-b verdict | Agent judges run first, then the user decides on the final package | Agent judges decide; the user reviews the delivered report afterwards |
| Spec gap found at 5-b | Listed in the final package | Escalation |
| Context-file proposal (`6-context-proposal.md`) | Approved or declined with the final package | Left for later review, linked from `6-report.md` |

**Auto-mode preconditions.** If any fails, tell the user which one and run in in mode instead.

1. `.loop/context.md` existed before this run.
2. Every 5-a gate is a runnable command, not a checklist item.
3. The risk tier is low or medium ([references/defaults.md](references/defaults.md)).
4. `verifier` resolves to a different model than `implementer` (see [Roster](#roster)).
5. The work is in a git repository, so the integrity checks can run.

These matter only when `--auto` was given. Check 1, 4, and 5 right after [0]. Check 2 and 3 at [2], once the slots are filled, and check 4 again if the user changes the roster at the spec stop. The spec package states the mode the run will actually use, so approving the spec also approves the mode.

**Escalations.** These are unplanned stops. Stop and ask in both modes when:

- an outcome-changing unknown appears that neither the repo nor `.loop/context.md` answers;
- a slice still fails 5-a after K re-runs;
- a 5-b round fails after R = 2 automatic send-backs;
- an integrity check fails in a way a re-run cannot repair (see [Integrity Checks](#integrity-checks));
- the work needs an action outside scope: destructive file or git operations, reading secrets (`.env*`, credentials), network writes, deploy, push, or commit;
- the risk turns out higher than assessed.

In auto mode, also stop when a 5-b finding cites no spec item (a spec gap) or the reviewer could not check a spec item.

Present every stop with [references/decision-package.md](references/decision-package.md). When the user chooses to stop, record it in `state.md`, leave the working tree as it is, and report the change list. Never revert work on your own.

## State on Disk

```text
.loop/context.md                 # [0] asset shared by every loop in this repo
.loop/YYMMDD-{slug}/             # one folder per task; date in KST: TZ='Asia/Seoul' date +"%y%m%d"
  state.md                       # mode, slots, resolved roster, current stage, attempt counters, open escalations
  context-draft.md               # only when [0] had to draft the context file; moved on spec approval
  1-intent.md  2-spec.md  2-plan-review.md  3-slices.md  slices/<id>.md
  gates/                         # gate scripts and fixtures you write; covered by the snapshot
  evidence/                      # before/after and baseline outputs for the 5-b judges; covered by the snapshot
  start.snap                     # tree snapshot taken before [4]
  5a-result.md  5b-changes.diff  5b-review.md
  6-context-proposal.md  6-report.md
  prompts/  logs/                # claude-cli prompts and output; logs/<run>.pre.snap per run, logs/latest.snap for resume
```

- Write each stage's result to disk and update `state.md` before moving on, so the loop survives `/compact` or a new session.
- Write file contents in the user's language. Redact any secret as `<REDACTED>`.
- Do not edit `.gitignore`. In the final report, mention that task folders can be ignored while `.loop/context.md` is worth committing.

## Integrity Checks

Agent-tool workers keep their full toolset, so verify what each run did instead of trusting its prompt. Use `bash ${CLAUDE_SKILL_DIR}/scripts/tree_snapshot.sh` (if `${CLAUDE_SKILL_DIR}` reads as a placeholder, use `~/.claude/skills/run-loop/scripts/tree_snapshot.sh`):

- `take` prints HEAD, an index fingerprint, and a content hash plus the executable bit for every changed or untracked file. Under `.loop/` it covers only the grading inputs: `context.md` and each task's context draft, intent, spec, slices, gate results, change-set diff, and every file under `gates/` and `evidence/`.
- `changed <snapshot>` prints the paths whose state differs from a saved snapshot, plus `!HEAD` or `!INDEX` when either moved.

The script only reads. It sees the repository and nothing else: it cannot see git-ignored files, and it cannot see what a worker writes elsewhere on the machine. Read-only prompts therefore send any scratch work to a temporary directory outside the repository and ask the worker to name it. Nothing enforces that for `runner=agent`; a `claude-cli` reviewer cannot write at all ([references/runners.md](references/runners.md)).

Do not write stage files while a worker is running, so that any `.loop/` path the script reports is the worker's doing. Save per-run snapshots as `logs/<run>.pre.snap`. Once a run's check has passed and its stage files are written, save `take` to `logs/latest.snap`, overwriting the previous one; [Resume](#resume) compares against it. Save it again whenever you yourself change a file the snapshot covers, such as `.loop/context.md` when you apply the context proposal at [6]. Apply the script at three points:

- **Start state.** Before [4], save `take` to `start.snap`. If a slice's allowed files appear in it, they were already dirty: escalate instead of mixing the user's uncommitted work into the loop. From here on, the loop's change list is `changed start.snap` minus its `.loop/` paths and minus the disposable outputs recorded in `5a-result.md`.
- **Read-only runs** (`plan-reviewer`, gate checks, `verifier`). Take a snapshot before the run. Afterwards `changed` must print nothing; if it prints anything, discard that run's verdict and escalate.
- **Implementer runs.** Take a snapshot before each slice or parallel group. Afterwards every changed path must be in the allowed files of a slice that just ran, and neither `!HEAD` nor `!INDEX` may appear. Files that appear as a side effect of running the gates or the code, such as caches and coverage data, are not violations: list them in `5a-result.md` as disposable outputs, and keep them out of the change list and the 5-b change set. A product file, a lockfile, or a grading input is never a disposable output.
  - A stray change to a file that was clean at start is a 5-a failure of the slice that made it: re-run that slice with the violation as its failure, telling it to undo the change.
  - A moved HEAD or index, a change under `.loop/`, a stray change to a file listed in `start.snap`, or a stray change whose slice cannot be identified is an escalation.

Outside a git repository the script exits with an error. Run in in mode and list "no integrity checks" as a known weakness in every package.

## Stage Markers

End every stage with one line that carries both markers, so the playbook's `tools/log2html.py` can tag the transcript. Every stage gets its own line, [0] included, even when you finish several stages in one step. Keep these Korean literals in any conversation language:

`[0] 맥락 · 현재 위치: 0번` · `[1] 의도 · 현재 위치: 1번` · `[2] 스펙 · 현재 위치: 2번` · `[3] 분해 · 현재 위치: 3번` · `[4] 구현 · 현재 위치: 4번` · `[5-a] 게이트 · 현재 위치: 5-a` · `[5-b] 외부 · 현재 위치: 5-b` · `[6] 개선 · 현재 위치: 6번`

Between stops, print only the marker plus at most one short status line.

## Roster

Roles: `implementer`, `plan-reviewer`, `verifier`. Fields per role: `runner` (`agent` | `claude-cli`), `subagent_type`, `model`, `effort`, and `view` (`tmux`, `claude-cli` only).

- Resolve each field in this order: what the user asked for in words for this run (in the invocation or at the spec stop), then the `## Agent roster` section of `.loop/context.md`, then the host default (`runner=agent`, everything else unset).
- For a field that resolves to nothing, omit the parameter. Do not choose a model or effort yourself, and do not substitute a value the runner rejects; report it instead.
- Never use `subagent_type: fork` for `plan-reviewer` or `verifier`: a fork inherits this conversation.
- Record the resolved roster in `state.md` and show it in the spec package.

**Comparing models.** Compare model families, not alias strings (an alias and a full model ID can name the same model).

- With `runner=agent`, an unset model counts as the orchestrator's own model. The Agent tool falls back to the agent definition, then the configured default, then the parent model, so this is an assumption: state it in the spec package.
- With `runner=claude-cli`, an unset model is the CLI's own default, which can differ from the orchestrator's. It is unknown until the run's log records it ([references/runners.md](references/runners.md)).
- When the two roles cannot be shown to differ, treat them as the same model. In mode allows a same-model reviewer but records "same-model reviewer" as a known weakness in `5b-review.md` and in the final package. Auto mode refuses it (precondition 4).

Launch details per runner: [references/runners.md](references/runners.md).

## Workflow

### [0] Context

1. Read `.loop/context.md`, then the repo's `AGENTS.md`/`CLAUDE.md`, README, and the files the goal points to. Identify the closest existing pattern to copy.
2. If `.loop/context.md` is missing, draft it from [references/context-template.md](references/context-template.md) at `.loop/YYMMDD-{slug}/context-draft.md`, using only facts found in the repo, and put everything inferred under "Unverified assumptions". Use the draft provisionally and present it in the [2] spec package instead of stopping now. Move it to `.loop/context.md` only when the user approves the spec package, so an unapproved draft never satisfies auto-mode precondition 1.
3. Never put secret values in the context file; record locations only.

### [1] Intent

1. Restate the goal and constraints in `1-intent.md`. List every assumption and mark each as answered (cite the path), defaulted (cite [references/defaults.md](references/defaults.md)), deferred (it does not change the outcome, so settle it as a decision in `2-spec.md`), or open (it changes the outcome).
2. Close open items yourself first by reading code, docs, and history. A read-only research subagent may help.
3. Ask the user only about open items that would change the outcome, in a single AskUserQuestion call (at most 4 questions, recommended option first). If nothing is open, do not stop.
4. Do not ask about gates, judges, the done definition, or K here; those go into the spec package.

### [2] Spec and Plan

1. Write `2-spec.md` as a checklist. Give each item an ID (`S1`, `S2`, ...) and its check method; for code, use test names. Keep facts, hypotheses, decisions, and unknowns separate. An item that cannot be checked is not spec: resolve it or move it to unknowns.
2. Fill the slots from `.loop/context.md`, else from the defaults: 5-a gates, 5-b judges, done definition, K, and risk tier. A gate you add yourself must run from the repository root in any later session: if it needs a script or a fixture, put that file under the task folder's `gates/`, never in a session scratch directory. Then check auto-mode preconditions 2 and 3.
3. Draft `3-slices.md` now (see [3]) so the user approves the destination and the route together.
4. Before the user sees anything, run `plan-reviewer` with [references/prompts.md](references/prompts.md#plan-review) on the intent, spec, slots, and slices. Save each round's findings and what you did about them to `2-plan-review.md`. If round 1 passes, stop there. If it fails, apply the fixes and run round 2 with a fresh agent, passing the round-1 findings and your changes. If round 2 also fails, apply its fixes but do not review again: list them in the package as applied without re-review. A finding you disagree with goes into the package as an open point in either round.
5. Present the spec package and ask: approve, change, or stop. This stop happens in both modes. If the user changes the spec, update the slices, and re-run the plan review only when the change is material. If the user changes the roster here, it applies to every run from this point; the plan review that already ran is not repeated for that reason alone.

### [3] Decompose

Each slice in `3-slices.md` has an ID, the files it may create, modify, or delete (including generated files such as lockfiles), the spec items it satisfies, its dependencies, its success check, and a parallel group. Slices in one parallel group share the working tree, so they must touch disjoint files; otherwise make them sequential. Size each slice to fit one subagent session.

### [4] Implement

1. Give each slice one implementer, with a prompt built from [references/prompts.md](references/prompts.md#slice). The prompt is self-contained: full spec items, allowed files, gate commands, report format. The worker cannot ask questions mid-run; if blocked, it stops and reports.
2. Launch all slices of a parallel group in one message. Wait for completion notifications; do not poll. Start a slice only after the slices it depends on have passed their success checks.
3. After each slice or group, save each worker's report to `slices/<id>.md`, run the implementer integrity check, and run each slice's success check when it is a command.
4. A worker that reports it was blocked, or a run that fails for a reason unrelated to the work (sign-in, a denied permission, no result), is not a 5-a attempt. Fix the cause and retry once; if it fails again, escalate.
5. Do not write or patch product code yourself.

### [5-a] Gates

1. Run the gate commands yourself and record each command in full, its exit code, and any failure excerpt in `5a-result.md`. Write the command itself, not a pointer to where it is defined: the verifier reads this file without the others. Running deterministic gates is a deliberate departure from the playbook's pure orchestrator: delegating them would add cost without adding independence.
2. A gate that is a checklist item rather than a command (coverage against the spec, source traceability) goes to a fresh agent launched with the `plan-reviewer` roster and [references/prompts.md](references/prompts.md#gate-check). Never give it to an implementer, and never pass slice reports.
3. On failure, re-run only the failing slice's implementer with the failure output appended. Attribute a failure by the files and spec items it names. When a test slice and an implementation slice disagree, decide from the spec text which one is wrong. If no slice owns the failure, add one fix slice for it at [3].
4. K is the number of re-runs one slice may use after 5-a failures (a failed gate or an out-of-scope change), counted over the whole loop; it does not reset after a 5-b send-back. When a slice fails again after its K-th re-run, escalate.
5. Passing is necessary, not sufficient. Always continue to 5-b.

### [5-b] External Verification

1. Build the change set from the loop's change list (see [Integrity Checks](#integrity-checks)): save `git diff <start HEAD> -- <changed tracked paths>` to `5b-changes.diff`, and list the changed untracked files separately. If no tracked path changed, write an empty `5b-changes.diff`; never run the diff with an empty path list, because that diffs the whole tree. If `start.snap` records `HEAD none` (a repository with no commit), there is nothing to diff against: write an empty diff and list every changed path as a new file. For work that produces documents or data rather than a diff, the produced artifacts are the change set. Do not use `git add -N` or otherwise touch the index.
2. Give judges only `2-spec.md`, the change set, `5a-result.md`, and before/after or baseline outputs. Save those outputs under the task folder's `evidence/` and pass their paths. Never pass slice reports, worker self-assessments, or this conversation.
3. Run deterministic judges first: before/after diffs, baseline comparisons, source-link checks. Then run `verifier` with [references/prompts.md](references/prompts.md#review). Save its output to `5b-review.md`.
4. Route the reviewer's result:
   - **A spec item is violated:** the spec was right and the work is wrong. Send it back to [4] for the affected slices with the finding as the failure, or to [3] if the slicing or wiring is wrong, then repeat 5-a and 5-b. Each send-back counts toward R = 2; when the review still fails after the second send-back, escalate.
   - **A finding cites no spec item:** a spec gap, and the spec belongs to the user. In mode: list it in the final package. Auto mode: escalate.
   - **A spec item could not be checked:** not a pass. Handle it like a spec gap.
   - **Notes** are not routed. Copy them into the final package or the report.
   - Never relabel a spec gap as a defect to avoid stopping. When unsure, treat it as a spec gap.
5. In mode: once the judges pass, or what remains needs a decision, write the context-file proposal ([6] step 2), then present the final package and ask: accept, send back to the spec (saying what is wrong), or stop. Auto mode: if every judge passes, continue to [6].
6. When the user sends the work back to the spec, return to [2] and get the changed spec approved again. That approval starts R again from zero. K keeps counting for a slice that keeps its ID and starts at zero for a new slice.

Automatic rework is a second deliberate departure. The playbook sends every 5-b failure back to [2]; here a failure that cites a spec item is reworked without the user, bounded by R, and anything that questions the spec itself still goes to the user.

### [6] Improve

1. Write `6-report.md`: what was built and how, gate and judge results, every finding fixed automatically, reviewer notes, and residual risks.
2. Write the proposed changes to `.loop/context.md` in `6-context-proposal.md`: new terms, decisions with rationale, rejected options, failure patterns as rules, and resolved or still-unverified assumptions. Apply them only after approval. Propose a roster value only when the user named it. If the run exposed a roster weakness such as a same-model reviewer, state the weakness and ask which value to use; do not pick a model, effort, or runner yourself.
3. Leave the work uncommitted. Offer a commit proposal and commit only after the user explicitly approves that proposal.

## Resume

When invoked with `resume [slug]`, or when an unfinished `.loop/*/state.md` matches the goal, read `state.md` and the stage files, then compare the working tree before continuing from the recorded stage. `changed start.snap` shows what the loop has changed so far. `changed logs/latest.snap` shows what changed after the last verified run: anything it prints happened outside the loop or in a run that was never checked, so say what changed and ask before continuing. If `start.snap` does not exist, the loop stopped before [4]; continue without calling `changed`. Do not re-ask questions answered in `1-intent.md` or re-approve an approved spec unless the repo changed in a way that invalidates it; if it did, say what changed.

## Rules

- Every retry loop is bounded: K re-runs per slice in 5-a, 2 plan-review rounds, R = 2 automatic 5-b send-backs per approved spec, 1 retry for a run that failed for unrelated reasons.
- Do not invent rules that are not in `.loop/context.md`; a missing rule is an open item.
- Separate verified facts from assumptions, and never state an unverified assumption as fact.
- Do not open `.env*` or credential files.
