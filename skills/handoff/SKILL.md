---
name: handoff
description: "Use this skill when the user requests a handoff or summary of the current conversation context for continuing work in a fresh session. Trigger on requests like \"handoff\", \"save context\", \"summary for next session\", \"export conversation\", \"save work state\", or any request to capture the current state of work for later continuation. Use when the user wants to transfer context to a new Claude instance, save progress before ending a session, or provide a summary for another agent to continue the task. Do NOT use for general summarization, code explanation, or documentation unrelated to handoff purposes."
---

# Handoff

## Purpose

Capture the current conversation context so a fresh Claude instance can continue the work without missing any information.

## Handoff Workflow

1. **Analyze the conversation**: Review the full conversation history
2. **Identify key elements**: Tasks attempted, what worked, what didn't work, current state
3. **Create handoff file**: Save as `handoffs/[task-slug]/HANDOFF-YYYY-MM-DD-HHMMSS.md`
   - **IMPORTANT**: Always save files in the workspace's `handoffs` folder, NOT in `.claude` folder
   - Extract task name from conversation, convert to slug (lowercase, hyphens for spaces)
   - Use current date and time (HANDOFF-YYYY-MM-DD-HHMMSS format) to prevent overwriting
   - **CRITICAL**: Always check if file exists before writing. If exists, add incrementing number: `HANDOFF-YYYY-MM-DD-HHMMSS-2.md`
4. **Provide summary**: Give the user a brief overview of what was captured

## Handoff Template

Create `handoffs/[task-slug]/HANDOFF-YYYY-MM-DD-HHMMSS.md` with the following structure:

```markdown
# [Task/Topic] - HANDOFF

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
ls -lt handoffs/[task-slug]/ | head -5  # Show recent files
```
```

## Real Example

```markdown
# DroidRun Knowledge System Improvement - HANDOFF

## Task Overview

Analyze DroidRun's Knowledge storage and retrieval system, create improvement plan, and implement changes.

## Current Progress (2026-02-10)

### 1. Completed Tasks
- ✅ Complete knowledge system structure analysis
- ✅ Add quality tracking fields and methods to models.py
- ✅ Ensure JSON compatibility in to_dict(), from_dict()

### 2. In Progress
- 🔄 Create quality.py file - KnowledgeQualityManager class implementation needed

### 3. Planned Improvements Summary
- Phase 1: Quality management (mostly complete)
- Phase 2: Semantic search

## Identified Issues
1. Keyword matching only, cannot capture semantic similarity
2. No feedback loop
3. No version control

## Implementation Order

### Phase 1 (Quick improvements - 2 days)
1. Create quality.py with KnowledgeQualityManager class
2. Add version control to storage.py

### Phase 2 (Medium effort - 1 week)
1. Implement semantic search with embeddings
2. Add feedback loop mechanism

## Key File Modifications

### Priority 1 (Core logic)
- **✅ Completed**: models.py - Added quality tracking fields and JSON methods
- **⏳ In progress**: quality.py - KnowledgeQualityManager class implementation
- **❌ Not started**: storage.py - Version control for knowledge entries

### Priority 2 (New features)
- **❌ Not started**: semantic_search.py - Embedding-based search implementation

## Notes

### What Worked
- Quality tracking fields fully implemented
- JSON compatibility ensured

### Issues Encountered and Resolved
- **Issue**: User cancelled Edit operation
  - **Cause**: Description was too brief
  - **Resolution**: Changed to explanation-then-approval approach per response-format.md rules
  - **Lesson**: Always provide detailed explanation before Edit call

### Current State
- Quality tracking fields and methods in models.py completed
- Only quality.py creation remaining

## Next Steps (Immediate Action Required)

### 1. Create KnowledgeQualityManager

**File**: droidrun/knowledge/quality.py

```python
from typing import List, Optional
from .models import Shortcut, Tip, KnowledgePool

class KnowledgeQualityManager:
    def __init__(self,
                 min_quality_score: float = 0.3,
                 max_failure_count: int = 5,
                 prune_unused_days: int = 90):
        self.min_quality_score = min_quality_score
        self.max_failure_count = max_failure_count
        self.prune_unused_days = prune_unused_days

    def prune_low_quality(self, pool: KnowledgePool) -> int:
        # Pruning logic
        pass
```

## Resuming Work
1. Read and understand this file
2. Create quality.py file
3. Add version control to storage.py

---

**Note**: For resuming work, load the most recent handoff file for the task:
```bash
ls -lt handoffs/knowledge-system-improvement/ | head -5  # Show recent files
```
```

## Best Practices

- **Be specific**: Include exact file paths, code, and commands
- **Focus on continuity**: Next agent should be able to continue without reading full conversation
- **Include failures**: Knowing what didn't work is as important as what worked
- **Keep it concise**: 100-300 lines - enough detail to continue, not a full transcript
- **Actionable next steps**: Include code so next agent can start immediately

## Creating the File

```bash
# Ensure directory exists (replace [task-slug] with actual task name)
# IMPORTANT: Always use workspace's handoffs folder, NOT `.claude` folder
mkdir -p handoffs/[task-slug]

# Use Write tool to create handoffs/[task-slug]/HANDOFF-YYYY-MM-DD-HHMMSS.md
# Example: HANDOFF-2026-02-11-143022.md

# Example for "Knowledge System Improvement" task:
mkdir -p handoffs/knowledge-system-improvement
# Then create: handoffs/knowledge-system-improvement/HANDOFF-2026-02-11-143022.md
```

## Storage Location

- **ALWAYS** save handoff files in the workspace's `handoffs` folder
- **NEVER** save files in `.claude` folder
- This ensures handoffs are project-specific and tracked in git when desired

## HANDOFF.md Writing Checklist

- [ ] Is task overview clear?
- [ ] Are completed (✅), in-progress (🔄), and pending (⏳) tasks distinguished?
- [ ] Is there a list of identified issues?
- [ ] Do next steps include executable code?
- [ ] Are file paths accurate?
- [ ] Do issues/resolved sections include lessons learned?
- [ ] Are resuming work steps clear?
