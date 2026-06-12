---
name: git-commit-message
description: "Analyze staged git changes, explain what changed, and propose a commit message. Use when the user requests 'generate commit message', 'create commit', 'git commit', or wants to commit staged changes."
---

# Generate Commit Message

Message format, language, and the approval-before-commit requirement are defined in the global rule (`~/.claude/rules/git-commit-guidelines.md`) — follow it. This skill only defines the workflow and the response format.

## Workflow

1. Check staged changes first: `git diff --staged` for content, `git diff --staged --name-only` for the file list.
2. **If staged changes exist, analyze only those** — do not mix in unstaged or untracked changes.
3. **If nothing is staged, don't stop** — look at the whole working tree (`git status`, `git diff`, untracked files), note that nothing is staged, and use judgment: propose a message covering the full change set, or suggest a sensible staging split when the changes clearly belong to separate commits. Do not stage files yourself unless the user asks.
4. Analyze what changed and why, file by file.
5. Propose a commit message using the response format below, then wait. Run `git commit` only after the user approves.

## Response Format

````markdown
## 📝 변경사항 분석 완료

Staged된 파일:
- [file1.ext](absolute/path/to/file1.ext) (신규/수정/삭제)
- [file2.ext](absolute/path/to/file2.ext) (신규/수정/삭제)

### 변경 내용

[파일별로 무엇이 왜 바뀌었는지 간단히]

---

## 제안하는 커밋 메시지

```
type: brief description
```

이 메시지가 괜찮으시면 커밋을 진행하겠습니다. 수정을 원하시면 말씀해주세요.
````
