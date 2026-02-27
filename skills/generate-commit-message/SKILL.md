---
name: generate-commit-message
description: "Analyze staged git changes and generate commit messages. Use when user requests 'generate commit message', 'create commit', 'git commit', or wants to commit staged changes."
---

# Generate Commit Message

## Workflow

1. Check staged changes with `git diff --staged`
2. List staged files with `git diff --staged --name-only`
3. Analyze changes and generate appropriate commit message
4. Propose message to user and get approval
5. Run `git commit` if approved

## Commit Message Guidelines

- Follow conventional commit format (feat, fix, refactor, docs, test, chore, etc.)
- Keep title concise and under 50 characters
- Use imperative mood ("add" not "added")
- Keep it simple - avoid overly complex messages
- Add body only when changes need explanation
- Mark breaking changes explicitly

## Response Format Template

After analyzing staged changes, respond in this format:

```markdown
## 📝 변경사항 분석 완료

Staged된 파일:
- [file1.ext](absolute/path/to/file1.ext) (신규/수정)
- [file2.ext](absolute/path/to/file2.ext) (신규/수정)

### 변경 내용

Brief summary of what changed in each file.

---

## 제안하는 커밋 메시지

```
type: brief description
```

이 메시지가 괜찮으시면 커밋을 진행하겠습니다. 수정을 원하시면 말씀해주세요.
```

## Examples

```
feat: add user authentication
```

```
fix(api): handle null server response
```

```
refactor(utils): improve date formatting logic

Removed duplicate code and improved readability.
```
