# Claude Code 설정 관리 저장소 — 작업 안내

`dev-ai-tools`의 submodule. 구조·스크립트·머신 종속 메커니즘 등 개요는 [README.md](./README.md)에 있다. 이 문서는 agent가 이 repo를 수정·관리할 때 지킬 규칙만 담는다.

경로 지도: `home/`만 `~/.claude/`로 sync · `home/settings.json`은 공통 baseline · `local/`은 머신 override(merge 입력, git-ignored).

## 작업 규칙

- **sync 게이트**: `~/.claude/` 반영(`claude-sync-to-home` 실행이든 수동 복사든)은 **사용자가 명시적으로 지시했을 때만**. 평소엔 `claude-diff-with-home`으로 차이만 확인해 공유한다.
- **sync 영역 경계**: `home/` 밖 파일을 sync 대상으로 옮기거나 그 반대를 하지 말 것.
- **settings.json은 merge**: `home/settings.json`(baseline) + `local/settings.override.json`(머신 값)을 deep-merge해 `~/.claude/settings.json`에 쓴다. baseline에 머신 종속 값을 넣지 말 것.
- **머신 종속 값**: `local/`의 `*.example`만 커밋. 실제 `settings.override.json`(광범위 권한 등 머신 종속 값)은 git-ignored — 커밋 금지. **strict JSON**으로 둘 것(주석 금지 — jq가 JSONC를 못 읽고 `http://` 값의 `//`와 충돌).
- **`home/CLAUDE.md`는 의도적 빈 파일** — 채우지 말 것(전역 지시는 `home/rules/`로 관리).
- **커밋 순서**: submodule에서 먼저 commit → 부모에서 포인터 commit.
- **메커니즘 무단 이식 금지**: 이 merge 방식을 codex(seed-if-absent)로, 또는 그 반대로 옮기지 말 것.
- **skill 작성**: 새 skill은 `reference-skills/`의 공식 예제를 참고해 만든다(참고 전용 submodule — 직접 수정 금지).
