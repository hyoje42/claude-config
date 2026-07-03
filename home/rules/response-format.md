# Response Format Rules

## 1. Explain Before and During Editing

When editing files, always explain **what** you're changing and **why** before making the change, so users can understand the modification in advance.

## 2. Code References

When mentioning code, use clickable markdown links with **absolute paths in the URL** but relative paths in the link text — e.g. `[helper.py:42-51](/home/user/project/src/utils/helper.py#L42-L51)` (single line: `#L120`). Do NOT use backticks, plain text, or relative paths in URLs — they are not clickable in the chat window.

## 3. Document Output Language

When writing, editing, or adding to documents or saved artifacts, use the language explicitly requested by the user. If none is specified, treat any language required by an invoked skill as user-requested; otherwise, match the existing document's language when appropriate, or use the language the user appears to prefer. Technical terms and code identifiers remain in original form.

## 4. Batch Related Changes Together

Group logically related changes in a single Edit proposal (e.g., function definition + call site together), rather than proposing overly granular changes one by one.
