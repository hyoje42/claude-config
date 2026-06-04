# Review Checklist

Use this checklist to pressure-test a change set. Focus on issues that could affect behavior, safety, or maintainability.

## Correctness

- Does the new logic do what the code comment, test, or commit message claims?
- Are there edge cases around empty input, null values, duplicate input, ordering, or partial failure?
- Does the change update all call sites, enum cases, schema paths, or feature-flag branches that depend on the old behavior?

## Data And State Safety

- Could this corrupt stored data, lose user input, or break migrations?
- Does the change alter serialization, schema shape, cache keys, or persistence format?
- Is rollback safe if the deployment is interrupted halfway through?

## Security And Permissions

- Does the change weaken auth, permission checks, tenant isolation, or secret handling?
- Are externally controlled values validated before use in file paths, queries, commands, or templates?
- Could logs, errors, or telemetry leak sensitive data?

## Failure Handling

- Are errors surfaced clearly, retried safely, or swallowed unexpectedly?
- Are cleanup paths, transactions, locks, or temporary resources handled on failure?
- Could timeouts, cancellations, or partial success leave the system in a bad state?

## Compatibility And Operations

- Does this break backward compatibility for APIs, configs, data contracts, or CLI behavior?
- Are config changes, migrations, rollout sequencing, or feature flags documented well enough to deploy safely?

## Performance

- Does the change put new work on a hot path?
- Could it increase query count, memory use, payload size, lock contention, or remote API traffic?
- Is caching still correct after the behavior change?

## Tests And Documentation

- Do tests cover the new behavior and the failure mode that is most likely to regress?
- Are tests asserting the right thing, or could they pass while the real bug remains?
- Are docs, examples, or operator notes missing for externally visible behavior changes?

## Reporting Guidance

- Lead with the issues that could block merge or cause user-facing damage.
- Skip minor style suggestions unless the user explicitly wants them.
- If no material issues are found, say that directly and mention any remaining uncertainty.
