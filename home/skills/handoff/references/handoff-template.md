# Handoff Template

Create `.handoffs/YYMMDD-{task-slug}/claude-handoff-YYYY-MM-DD-HHMMSS.md` with the following structure. Keep the handoff self-contained: a new agent must not need the original session or earlier handoffs to understand and continue the work.

Keep the Task Mission, Decision Record, Verified Current State, Open Questions, Safety Boundaries, and Next Actions sections. For other sections, drop parts that genuinely do not apply rather than leaving empty placeholders. Add detail when it preserves continuation-critical context; do not shorten the handoff to meet an arbitrary line target.

Translate section headings and prose into the user's explicitly requested language; if no language is specified, use the user's preferred language. Keep file paths, code identifiers, and commands unchanged.

```markdown
# [Task/Topic] - HANDOFF

## Continuity References

- **Source session**: [session ID/link if available, otherwise "not recorded"]
- **Previous handoff**: `.handoffs/YYMMDD-{task-slug}/{author}-handoff-YYYY-MM-DD-HHMMSS.md` [or "none"]
- **Created**: YYYY-MM-DD HH:MM KST

The previous handoff is provenance only. This file integrates all still-relevant context and stands alone.

## Task Mission

### User Goal

[What the user ultimately wants and why]

### Success Criteria

- [Observable condition that means the task is complete]
- [Required validation or deliverable]

### Scope and Non-Goals

- **In scope**: [work included]
- **Out of scope**: [work intentionally excluded]

### Explicit User Constraints and Preferences

- [Approval gate, prohibited action, preferred approach, output requirement, etc.]
- [Use brief exact wording when paraphrasing could alter the user's intent]

## Decision Record

### Accepted Decisions

1. **Decision**: [what was decided]
   - **Why**: [rationale and evidence]
   - **Consequence**: [what this enables or rules out]

### Rejected or Deferred Alternatives

1. **Alternative**: [option not chosen]
   - **Reason**: [why it was rejected or deferred]
   - **Revisit when**: [condition that would change the decision, if any]

## Verified Current State

- **Last verified**: YYYY-MM-DD HH:MM KST
- **Workspace/repository root**: `/absolute/path`
- **Branch / HEAD**: `[branch]` / `[commit SHA]` [or "not a Git repository"]
- **Worktree state**: [staged / unstaged / untracked / clean; include the relevant `git status --short` facts]
- **Relevant external or sync state**: [state that affects continuation, or "not applicable"]

### Validation Performed

| Command/check | Result | What it establishes |
|---|---|---|
| `[exact command]` | pass/fail/[observed output] | [claim supported by the check] |

### Drift Warning

[Identify volatile claims that the next agent must re-check, or "none known"]

## Work Progress

### Completed

- ✅ [Completed work and durable outcome]

### In Progress

- 🔄 [Partially completed work, including its exact stopping point]

### Pending

- ⏳ [Work not started or awaiting a decision]

## Key Artifacts and Modifications

| Path/artifact | State | What changed or why it matters |
|---|---|---|
| `path/to/file` | modified/new/reference-only | [continuation-relevant detail] |

Include code inline only when it does not exist in a durable file and is necessary to continue.

## Session-Only Context

### Discoveries and Reasoning

- [Important context learned in conversation or tool output that is not evident from the repository]

### What Worked

- [Successful approach and why it worked]

### Failed Approaches and Lessons

- **Attempt**: [what was tried]
  - **Observed result**: [what happened]
  - **Cause or current theory**: [verified cause or explicitly labeled inference]
  - **Lesson**: [what the next agent should do differently]

## Assumptions and Unverified Claims

- **Assumption/inference**: [claim not yet verified]
  - **Basis**: [why it seems plausible]
  - **How to verify**: [specific check]

Use "none" when every continuation-critical claim has been verified. Do not present assumptions as current state.

## Open Questions and Required Decisions

1. **Question/decision**: [what remains unresolved]
   - **Owner**: user / agent / external party
   - **Needed before**: [work that must wait for the answer]
   - **Options and tradeoffs**: [known choices]

## Safety Boundaries and Approval Gates

- **Do not**: [action prohibited by the user, repository rules, or task scope]
- **Requires explicit approval**: [sync, commit, deploy, destructive operation, scope expansion, etc.]
- **Preserve**: [user work or state that must not be overwritten]

## Next Actions

### 1. [Highest-priority next action]

- **Objective**: [what this action should accomplish]
- **Files/area**: `path/to/file`
- **Action or commands**:

  ```bash
  [exact command when applicable]
  ```

- **Expected result**: [observable success condition]
- **Stop/ask condition**: [when not to continue without the user]
- **Verification**: [command or concrete check]

### 2. [Following action]

[Repeat the same fields]

## Resume Checklist

1. Read the applicable agent instructions and this handoff.
2. Compare the recorded branch, `HEAD`, worktree, files, and external state with the current environment.
3. Report and resolve meaningful drift before trusting state-dependent claims.
4. Preserve the explicit user constraints, rejected alternatives, and approval gates above.
5. Start with Next Action 1 unless new user input changes the priority.

---

To locate related handoffs:

```bash
ls -dt .handoffs/*-{task-slug} | head -5                    # Recent task folders
ls -lt .handoffs/*-{task-slug}/*-handoff-*.md | head -5     # Recent files (any author)
```
```
