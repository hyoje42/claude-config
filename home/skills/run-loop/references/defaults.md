# Defaults

Use these when `.loop/context.md` does not set a slot. Every default used must be listed as such in the spec package.

## Gates and Judges by Task Type

| Task | 5-a gates (cheap, deterministic) | 5-b judges (external) |
|---|---|---|
| Code change | Lint, type check, unit tests on touched code | Before/after output diff, baseline comparison, `reviewer-5b` |
| Report or plan | Coverage against the spec, source traceability, reproducible numbers | `reviewer-5b` checks sources and counter-evidence; domain and data owners in in mode |
| Data analysis | Re-running the query yields the same values; period and row counts match | Recompute with `reviewer-5b`; data owner in in mode |
| Summary | Every sentence traces to the source text | `reviewer-5b` compares against the source; source author in in mode |
| Research | Every claim has a source link that resolves | `reviewer-5b` cross-checks claims |

Non-code work has gates too: coverage, traceability, and reproducibility. A gate written as a command is run by the orchestrator. A gate that stays a checklist item is run by a gate-check agent ([prompts.md](prompts.md#gate-check)), never by the implementer, and it keeps the task out of on mode until someone turns it into a command.

## Risk Tiers

| Tier | Examples | 5-b requirement | On mode |
|---|---|---|---|
| Low | Meeting summary, wording edits | Source comparison | Allowed |
| Medium | Interview analysis, plan draft, refactoring | Sources, counter-evidence, one reviewer | Allowed |
| High | Prioritization, metric conclusions, schema changes | Cross-team review and explicit user approval | Refused |
| Very high | Pricing, legal, personal data, automated execution | Approved sources only, audit log, owner approval | Refused |

When a task matches no example, pick the tier whose examples would cost about as much if the result were wrong, and say why in the spec package. Take the higher tier only when two tiers fit equally well.

## Limits

| Limit | Default |
|---|---|
| K (re-runs of one slice after a failed gate or an out-of-scope change, counted over the whole loop) | 3 for documents and analysis, 6 for code |
| Plan-review rounds at [2] | 2 |
| R (automatic send-backs from 5-b; the reviewer runs at most R + 1 times) | 2 |
| Retries of a run that failed for reasons unrelated to the work | 1 |
| Questions per intent stop | 4 (one AskUserQuestion call) |
