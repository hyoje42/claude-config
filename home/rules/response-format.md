# Response Format Rules

## 1. Explain Before and During Editing

When editing files, always explain **what** you're changing and **why** before making the change, so users can understand the modification in advance.

## 2. Code References

When mentioning code, use clickable markdown links with **absolute paths in URL**, relative paths in text:

```markdown
[helper.py:120](/home/user/project/src/utils/helper.py#L120)
[helper.py:42-51](/home/user/project/src/utils/helper.py#L42-L51)
```

Do NOT use backticks, plain text, or relative paths in URLs — they are not clickable in the chat window.

## 3. Plan Mode Output Language

All plan mode output must be written in the user's preference language. Technical terms and code identifiers remain in original form.

## 4. Batch Related Changes Together

Group logically related changes in a single Edit proposal (e.g., function definition + call site together), rather than proposing overly granular changes one by one.
