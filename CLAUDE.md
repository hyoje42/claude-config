# Claude Code 설정 관리 저장소

Claude Code를 더 편하게 사용하기 위한 커스텀 skill, rule, 설정을 만들고 `~/.claude/`에 동기화하는 저장소.

## 구조

- `home/` — `~/.claude/`로 그대로 sync되는 영역. 이 폴더 안의 구조는 `~/.claude/` 레이아웃을 미러링한다.
  - `home/CLAUDE.md` — **의도적으로 빈 파일.** 전역 지시는 `home/rules/`로만 관리하고, 이 파일은 `~/.claude/CLAUDE.md`를 빈 상태로 유지하기 위한 placeholder다. 내용을 채우지 말 것.
  - `home/rules/` — Claude Code 전역 규칙 (응답 형식, 도구 사용, git 커밋, Python 가이드라인)
  - `home/skills/` — 커스텀 skill 정의
  - `home/settings.json` — 권한, 언어 등 Claude Code 설정
- `reference-skills/` — [anthropics/skills](https://github.com/anthropics/skills) submodule (skill 작성 시 참고용, 수정 금지)
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.** 사유는 [outdated/README.md](./outdated/README.md) 참고.
- `CLAUDE.md` (이 문서) — repo 자체를 다룰 때 참고하는 meta 문서. **sync 대상 아님.**

## 스크립트

- `claude-sync-to-home` — `home/` 내용을 `~/.claude/`로 복사. **사용자가 명시적으로 지시했을 때만 실행할 것.**
- `claude-diff-with-home` — `home/`과 `~/.claude/` 간 차이 확인

## 작업 흐름

1. 이 repo의 `home/` 하위에서 rules/skills/settings.json 수정
2. `./claude-diff-with-home`으로 차이 확인 후 사용자에게 결과 공유
3. **사용자의 명시적 지시가 있을 때만** `./claude-sync-to-home`으로 `~/.claude/`에 반영 (스크립트 대신 수동 복사 등으로 `~/.claude/`를 변경하는 것도 동일하게 지시가 필요)
4. Git commit으로 변경 이력 관리

## Skill 작성 가이드

새로운 skill을 만들 때는 반드시 `reference-skills/` 내의 공식 예제를 참고할 것.

- skill 구조와 포맷: `reference-skills/spec/`, `reference-skills/template/`
- 실제 skill 예시: `reference-skills/skills/` 하위 디렉토리들
- `reference-skills/`는 참고 전용 submodule이므로 직접 수정하지 말 것
