# Claude Code 설정 관리 저장소

Claude Code를 더 편하게 사용하기 위한 커스텀 skill, rule, 설정을 만들고 `~/.claude/`에 동기화하는 저장소.

## 구조

- `rules/` — Claude Code 전역 규칙 (응답 형식, 도구 사용, Python 가이드라인)
- `skills/` — 커스텀 skill 정의
- `settings.json` — 권한, 언어 등 Claude Code 설정
- `reference-skills/` — [anthropics/skills](https://github.com/anthropics/skills) submodule (skill 작성 시 참고용, 수정 금지)

## 스크립트

- `claude-sync-to-home` — 이 repo의 rules, skills, settings.json을 `~/.claude/`로 복사
- `claude-diff-with-home` — 이 repo와 `~/.claude/` 간 차이 확인

## 작업 흐름

1. 이 repo에서 rules/skills/settings.json 수정
2. `./claude-diff-with-home`으로 차이 확인
3. `./claude-sync-to-home`으로 `~/.claude/`에 반영
4. Git commit으로 변경 이력 관리

## Skill 작성 가이드

새로운 skill을 만들 때는 반드시 `reference-skills/` 내의 공식 예제를 참고할 것.

- skill 구조와 포맷: `reference-skills/spec/`, `reference-skills/template/`
- 실제 skill 예시: `reference-skills/skills/` 하위 디렉토리들
- `reference-skills/`는 참고 전용 submodule이므로 직접 수정하지 말 것
