# Claude Code 설정 관리 저장소

Claude Code를 더 편하게 사용하기 위한 커스텀 skill, rule, 설정을 만들고 `~/.claude/`에 동기화하는 저장소.

사람용 개요는 [README.md](./README.md)에 있다. 이 문서는 agent를 위한 안내다.

## 구조

- `home/` — `~/.claude/`로 sync되는 영역. 이 폴더 안의 구조는 `~/.claude/` 레이아웃을 미러링한다.
  - `home/CLAUDE.md` — **의도적으로 빈 파일.** 전역 지시는 `home/rules/`로만 관리하고, 이 파일은 `~/.claude/CLAUDE.md`를 빈 상태로 유지하기 위한 placeholder다. 내용을 채우지 말 것.
  - `home/rules/` — Claude Code 전역 규칙 (응답 형식, 도구 사용, git 커밋, Python 가이드라인)
  - `home/skills/` — 커스텀 skill 정의
  - `home/settings.json` — Claude Code 설정의 **공통 baseline**(권한·언어 등, git 커밋 대상). 머신 종속 값은 여기 두지 않는다 → 아래 "Local 전용 설정" 절 참고. (sync 시 그대로 복사되지 않고 merge를 거칠 수 있음)
- `local/` — **머신 종속 설정을 두는 곳 (sync 대상 아님).**
  - `local/settings.override.json` — 이 머신 전용 값(프록시·사내 CA·광범위 권한, strict JSON). **git-ignored.** sync 시 baseline과 merge되어 `~/.claude/settings.json`에 반영된다.
  - `local/settings.override.json.example` — 위 파일의 커밋용 템플릿(주석 포함 참고용). 복사 후 주석을 지워 strict JSON으로 저장한다.
- `reference-skills/` — [anthropics/skills](https://github.com/anthropics/skills) submodule (skill 작성 시 참고용, 수정 금지)
- `outdated/` — 퇴역한 skill·rule의 기록용 보관소. **sync 대상 아님.** 사유는 [outdated/README.md](./outdated/README.md) 참고.
- `CLAUDE.md`(= `@AGENTS.md`) / `AGENTS.md` (이 문서) — repo 자체를 다룰 때 참고하는 meta 문서. **sync 대상 아님.**

## Local 전용 설정 (settings.json merge)

`~/.claude/settings.json`만 **모든 디렉터리에서 전역 적용**된다. (`~/.claude/settings.local.json`은 홈 디렉터리에서 claude를 실행할 때만 먹는 project-local 취급이라 전역 적용 수단이 아니다.) 그래서 머신 종속 값을 **git에 커밋하지 않으면서 전역 적용**하려면, 공통 baseline과 머신 override를 sync 시점에 합친다.

- **baseline**: `home/settings.json` (커밋, 공통 설정)
- **override**: `local/settings.override.json` (git-ignored, 머신 값, **strict JSON — 주석 금지**. jq가 JSONC를 못 읽고 `http://...` 값의 `//`와 충돌)
- **merge**: `claude-merge-settings`가 deep-merge — 객체=키 병합 / 배열(`permissions.allow` 등)=합집합 / 스칼라=override 우선
- override가 **없으면** settings.json은 그냥 baseline 그대로 sync된다.

`claude-sync-to-home`이 sync 중 자동으로 merge해서 `~/.claude/settings.json`에 쓰고, `claude-diff-with-home`은 merge 결과를 기준으로 diff를 보여준다(= sync하면 무엇이 바뀔지). 실제 머신 값(프록시 IP·사내 CA 경로 등)은 `local/`에만 두고 절대 커밋하지 말 것.

## 스크립트

- `claude-sync-to-home` — `home/`을 `~/.claude/`로 복사. settings.json은 override가 있으면 `home/settings.json` + `local/settings.override.json`을 merge해 기록한다(없으면 그대로 복사). **사용자가 명시적으로 지시했을 때만 실행할 것.**
- `claude-diff-with-home` — `home/`과 `~/.claude/` 간 차이 확인. settings.json은 merge 결과 기준으로 비교한다.
- `claude-merge-settings` — baseline + override를 deep-merge (위 두 스크립트가 내부적으로 사용하며 단독 실행도 가능). `jq` 필요.

## 작업 흐름

1. 공통 설정은 `home/` 하위(rules/skills/`home/settings.json`)에서, **머신 종속 값은 `local/settings.override.json`**에서 수정
2. `./claude-diff-with-home`으로 차이 확인(settings.json은 merge 결과 기준) 후 사용자에게 결과 공유
3. **사용자의 명시적 지시가 있을 때만** `./claude-sync-to-home`으로 `~/.claude/`에 반영 (스크립트 대신 수동 복사 등으로 `~/.claude/`를 변경하는 것도 동일하게 지시가 필요)
4. Git commit으로 변경 이력 관리

## Skill 작성 가이드

새로운 skill을 만들 때는 반드시 `reference-skills/` 내의 공식 예제를 참고할 것.

- skill 구조와 포맷: `reference-skills/spec/`, `reference-skills/template/`
- 실제 skill 예시: `reference-skills/skills/` 하위 디렉토리들
- `reference-skills/`는 참고 전용 submodule이므로 직접 수정하지 말 것
