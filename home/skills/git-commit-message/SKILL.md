---
name: git-commit-message
description: "Analyze staged git changes, explain what changed, and propose a commit message. Use when the user requests 'generate commit message', 'create commit', 'git commit', or wants to commit staged changes."
---

# Generate Commit Message

## Commit Rules

- Never run `git commit` on your own initiative. When asked to commit or to generate a message, propose the message first and run `git commit` only after the user approves. Ambiguous phrasing like "sync to git" does not mean commit.
- Always write commit messages in English, even when the conversation is in another language.
- Follow conventional commit format (feat, fix, refactor, docs, test, chore, etc.).
- Keep the title concise (under 50 characters) and in imperative mood ("add", not "added"); mark breaking changes explicitly.
- Use a subject-only message only for small, obvious changes such as typo fixes, formatting-only edits, or narrow single-file docs updates.
- Add a body when the staged change affects behavior, sync/install flows, configuration, security/secrets handling, migration policy, multiple files, multiple repositories/submodules, or when the "why" is not obvious from the title.
- When proposing multiple commits, evaluate each commit independently and include a body for any non-trivial commit.
- Do NOT add AI co-author trailers (e.g., `Co-Authored-By: Claude`, `Co-Authored-By: Codex`) or generator footers (e.g., `🤖 Generated with ...`).

## Workflow

1. Check staged changes first: `git diff --staged` for content, `git diff --staged --name-only` for the file list.
2. **If staged changes exist, analyze only those** — do not mix in unstaged or untracked changes.
3. **If nothing is staged, don't stop** — inspect the working tree (`git status`, `git diff`, untracked files), then propose which files to stage (grouped into separate commits when they clearly differ) plus each group's message, in the same response. Prefer changes you made this session; flag any you didn't rather than forcing them in. Don't run `git add`/`git commit` until the user approves.
4. Analyze what changed and why, file by file.
5. Propose a commit message using the response format below, then wait for the user.

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

(본문은 non-trivial한 변경일 때만: 관련된 why/how, behavior·policy·migration·safety 영향)
```

이 메시지가 괜찮으시면 커밋을 진행하겠습니다. 수정을 원하시면 말씀해주세요.
````
