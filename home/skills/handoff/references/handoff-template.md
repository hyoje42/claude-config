# Handoff Template

Create `.handoffs/YYMMDD-{task-slug}/claude-handoff-YYYY-MM-DD-HHMMSS.md` with the following structure. Drop sections that genuinely do not apply rather than leaving them empty.

```markdown
# [Task/Topic] - HANDOFF

## Reference Handoff (if continuing from previous handoff)

**Previous Handoff**: `.handoffs/YYMMDD-{task-slug}/{author}-handoff-YYYY-MM-DD-HHMMSS.md`

This handoff continues work from a previous session. The following sections integrate previous progress with new developments.

---

## Task Overview

[Brief description of what this task is about - 1-2 sentences]

## Current Progress (Date)

### 1. Completed Tasks

- ✅ [Completed task 1]
- ✅ [Completed task 2]

### 2. In Progress

- 🔄 [In-progress task]
- ⏳ [Pending task]

### 3. Planned Improvements Summary

- [List of planned improvements]

## Identified Issues

1. [Issue 1]
2. [Issue 2]

## Implementation Order

### Phase 1 (Quick improvements - duration)
1. [Task 1]
2. [Task 2]

### Phase 2 (Medium effort - duration)
1. [Task 3]
2. [Task 4]

## Key File Modifications

### Priority 1 (Core logic)
- **✅ Completed**: filename - description
- **⏳ In progress**: filename - description
- **❌ Not started**: filename - description

### Priority 2 (New features)
- **❌ Not started**: filename - description

## Notes

### What Worked
- [Successfully completed items]

### Issues Encountered and Resolved
- **Issue**: [The issue encountered]
  - **Cause**: [Cause]
  - **Resolution**: [How it was resolved]
  - **Lesson**: [What was learned]

### Current State
- [Current work state]

## Next Steps (Immediate Action Required)

### 1. [Next step title]

**File**: [filepath/filename]

[Code or detailed description]

## Resuming Work

1. Read and understand this file
2. [Next task]
3. [Next task]

---

**Note**: For resuming work, load the most recent handoff file for the task:
```bash
ls -dt .handoffs/*-{task-slug} | head -5                    # Recent task folders
ls -lt .handoffs/*-{task-slug}/*-handoff-*.md | head -5     # Recent files (any author)
```
```
