# Context File Template

Template for `.loop/context.md`, the stage-0 asset shared by every loop in a repo. Keep the `##` headings as written so later loops can find each section; write the bodies in the user's language.

Rules for drafting:

- Fill a section only with facts found in the repo, and cite the path for each.
- Put anything inferred under "Unverified assumptions", never in another section.
- Gates, Judges, and Agent roster hold choices rather than facts. In a draft, fill them with what you propose and mark each line `(proposed)`. The user settles them by approving the draft with the spec package; remove the marks when the draft becomes `.loop/context.md`.
- Leave a section with `-` when nothing is known yet; it grows through [6].
- Record locations of secrets, never their values.

```markdown
# Loop Context

## Terms
- <term>: <meaning>. Start with words an outsider would misread.

## Sources
- <what>: <path or location>. Mark which is the original and which is derived.

## Decisions
- YYYY-MM-DD <decision>. Why: <reason>. Do not revert: <yes/no>.

## Output formats
- <artifact type>: <standard shape, with one example path>.

## Forbidden
- <what must not be done or touched>.

## Unverified assumptions
- <assumption>. How to verify: <check>. Never treat these as facts.

## Gates
- <task type>: `<5-a command>`

## Judges
- <task type>: <5-b judge: before/after diff, baseline comparison, reviewer agent, owner review>

## Agent roster
- implementer: runner=agent
- plan-reviewer: runner=agent
- reviewer-5b: runner=agent, model=<a different model than implementer>
```

Roster fields left out resolve to the host default (see SKILL.md, Roster). On mode needs `reviewer-5b` and `implementer` to be shown to run on different models, so set `model` for both when the roster uses `runner=claude-cli`.
