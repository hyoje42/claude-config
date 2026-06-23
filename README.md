# Claude Code 설정 관리 저장소

Claude Code를 더 편하게 사용하기 위한 커스텀 skill, rule, 설정을 만들고 `~/.claude/`에 동기화하는 저장소.

이 문서는 사람용 개요다. agent용 안내는 [AGENTS.md](./AGENTS.md)(= `CLAUDE.md`)에 있다.

## 구조

- `home/` — `~/.claude/`로 sync되는 영역. 폴더 구조가 `~/.claude/` 레이아웃을 그대로 미러링한다.
  - `home/CLAUDE.md` — `~/.claude/CLAUDE.md`를 빈 상태로 두기 위한 placeholder(의도적 빈 파일). 전역 지시는 `home/rules/`로 관리한다.
  - `home/rules/` — Claude Code 전역 규칙(응답 형식·도구 사용·git 커밋·Python 등)
  - `home/skills/` — 커스텀 skill 정의
  - `home/settings.json` — Claude Code 설정의 **공통 baseline**(권한·언어 등). git에 커밋되며, 머신 종속 값은 여기 두지 않는다.
- `local/` — **머신 종속 설정을 두는 곳 (sync 대상 아님).**
  - `local/settings.override.json` — 이 머신에만 적용할 값(프록시·사내 CA·광범위 권한 등). **git-ignored.** sync 대상이 아니라 merge 재료로만 쓰인다.
  - `local/settings.override.json.example` — 위 파일의 커밋용 템플릿(주석 포함). 복사해서 쓴다.
- `reference-skills/` — [anthropics/skills](https://github.com/anthropics/skills) submodule(skill 작성 참고용, 수정 금지)
- `outdated/` — 퇴역한 skill·rule 보관소. **sync 대상 아님.**
- `README.md`(이 문서) / `AGENTS.md`(= `CLAUDE.md`) — repo 관리용 meta 문서. **sync 대상 아님.**
- `_backup/` — `~/.claude` 동기화 전 백업. **수정 금지.**

## 스크립트

- `claude-sync-to-home` — `home/` 내용을 `~/.claude/`로 복사. settings.json은 머신 override가 있으면 merge해서 기록한다(아래 참고). **사용자가 명시적으로 지시했을 때만 실행한다.**
- `claude-diff-with-home` — `home/`과 `~/.claude/`의 차이 확인. settings.json은 merge 결과를 기준으로 보여준다(= sync하면 무엇이 바뀔지).
- `claude-merge-settings` — baseline과 override를 deep-merge하는 도구. 위 두 스크립트가 내부적으로 사용한다(`jq` 필요).

## 작업 흐름

1. 공통 설정은 `home/`(rules·skills·`home/settings.json`)에서, 머신 종속 값은 `local/settings.override.json`에서 수정한다.
2. `./claude-diff-with-home`으로 차이를 확인한다.
3. 필요할 때 `./claude-sync-to-home`으로 `~/.claude/`에 반영한다.
4. `git commit`으로 변경 이력을 남긴다(`local/`은 커밋되지 않는다).

## 머신 종속 설정 (local override + merge)

프록시·사내 CA·광범위 권한 같은 **이 머신에만 필요한 값**은 git에 올리지 않으면서도 **모든 디렉터리에서 전역 적용**되어야 한다. Claude Code에서 전역 적용되는 설정은 `~/.claude/settings.json` 하나뿐이므로(`~/.claude/settings.local.json`은 홈 디렉터리에서 실행할 때만 먹는 함정이다), 공통 설정과 머신 값을 sync 시점에 합쳐서 그 파일에 쓴다.

**셋업**

1. `local/settings.override.json.example`을 복사한다.
2. **주석을 모두 지우고** 실제 값(프록시 IP·사내 CA 절대경로 등)을 채운다. → strict JSON이어야 한다(`jq`가 JSONC 주석을 못 읽고, `http://...` 값 안의 `//`와도 충돌한다).
3. `local/settings.override.json`으로 저장한다. (이 파일은 git-ignored라 커밋되지 않는다)

**동작**

- `claude-sync-to-home` 실행 시 `home/settings.json`(baseline) + `local/settings.override.json`(override)을 deep-merge해서 `~/.claude/settings.json`에 쓴다.
  - 객체: 키 병합 / 배열(`permissions.allow` 등): 합집합 / 스칼라: override 우선
- override가 **없으면** settings.json은 그냥 baseline 그대로 복사된다.
- `claude-diff-with-home`은 merge 결과를 기준으로 diff를 보여주므로, sync 전에 실제 반영될 내용을 확인할 수 있다.

> 실제 프록시 IP·사내 도메인·CA 경로 등 내부 인프라 정보는 `local/`에만 두고 **절대 커밋하지 말 것.** 관련 배경은 [../docs/codex-proxy-ssl-login.md](../docs/codex-proxy-ssl-login.md)(프록시·사내 CA) 참고.

## Skill 작성 가이드

새 skill은 반드시 `reference-skills/`의 공식 예제를 참고해서 만든다.

- skill 구조·포맷: `reference-skills/spec/`, `reference-skills/template/`
- 실제 예시: `reference-skills/skills/` 하위
- `reference-skills/`는 참고 전용 submodule이므로 직접 수정하지 않는다.
