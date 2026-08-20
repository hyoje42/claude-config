# Claude Code 설정 관리 저장소

Claude Code를 더 편하게 사용하기 위한 커스텀 skill, rule, 설정을 만들고 `~/.claude/`에 동기화하는 저장소.

## 구조

- `home/` — `~/.claude/`로 sync되는 영역. 폴더 구조가 `~/.claude/` 레이아웃을 그대로 미러링한다.
  - `home/CLAUDE.md` — `~/.claude/CLAUDE.md`를 빈 상태로 두기 위한 placeholder(의도적 빈 파일). 전역 지시는 `home/rules/`로 관리한다.
  - `home/rules/` — Claude Code 전역 규칙(응답 형식·도구 사용·git 커밋·Python·agent 지시 파일 작성 등)
  - `home/skills/` — 커스텀 skill 정의
  - `home/output-styles/` — output style 정의. `rules/`보다 강한 **시스템 프롬프트 층위**에 놓이는 지침이며, 기본값은 `home/settings.json`의 `outputStyle`로 지정한다(아래 참고).
  - `home/settings.json` — Claude Code 설정의 **공통 baseline**(권한·언어·attribution 기본값 등). git에 커밋되며, 머신 종속 값은 여기 두지 않는다.
- `local/` — **머신 종속 설정을 두는 곳.** `local/*`는 git-ignored라 이 머신에만 적용된다.
  - `local/settings.override.json` — 이 머신에만 적용할 settings.json 값(광범위 권한 등). sync 대상이 아니라 merge 재료로만 쓰인다.
  - `local/settings.override.json.example` — 위 파일의 커밋용 템플릿(주석 포함). 복사해서 쓴다.
  - `local/` 일반 파일 오버라이드 — `home/`과 동일한 미러 구조(`local/rules/`, `local/skills/`, 최상위 파일)로 **이 머신에만 쓸 파일**을 둘 수 있다. sync 시 `home/` 적용 뒤 `~/.claude/`로 덮어쓴다. `home/`과 같은 경로가 중복되면 sync가 거부된다(아래 참고). `settings.override.json`·`*.example`·`.synced`는 제외.
- `reference-skills/` — [anthropics/skills](https://github.com/anthropics/skills) submodule(skill 작성 참고용, 수정 금지)
- `outdated/` — 퇴역한 skill·rule 보관소. **sync 대상 아님.** 퇴역 사유는 [outdated/README.md](./outdated/README.md) 참고.
- `README.md`(이 문서) — 이 repo 설명. / `AGENTS.md`(= `CLAUDE.md`) — agent 작업 규칙. 둘 다 **sync 대상 아님.**
- `_backup/` — `~/.claude` 동기화 전 백업. **수정 금지.**

## 스크립트

- `claude-sync-to-home` — `home/` 내용을 `~/.claude/`로 복사. settings.json은 머신 override가 있으면 merge해서 기록한다(아래 참고). **사용자가 명시적으로 지시했을 때만 실행한다.**
- `claude-diff-with-home` — `home/`과 `~/.claude/`의 차이 확인. settings.json은 merge 결과를 기준으로 보여준다(= sync하면 무엇이 바뀔지). 실체는 `claude-sync-to-home --dry-run`의 얇은 래퍼라, 무엇이 바뀌는지 계산하는 로직은 `claude-sync-to-home` 한 곳에만 있다(관리 디렉터리 추가 등은 그 파일만 고치면 된다).
- `claude-merge-settings` — baseline과 override를 deep-merge하는 도구. 위 두 스크립트가 내부적으로 사용한다(`jq` 필요).
- `tests/sync-home.sh` — 임시 HOME과 repo 사본에서 diff/sync를 실행해, dry-run이 아무것도 쓰지 않는지·dry-run이 보고한 항목이 sync에서 그대로 적용되는지·sync 직후 재실행이 멱등한지·무효 override/경로 중복을 거부하는지 검증한다. 실제 `~/.claude`는 건드리지 않는다.

## 작업 흐름

1. 공통 설정은 `home/`(rules·skills·output-styles·`home/settings.json`)에서, 머신 종속 값은 `local/settings.override.json`에서 수정한다.
2. `./claude-diff-with-home`으로 차이를 확인한다.
3. 필요할 때 `./claude-sync-to-home`으로 `~/.claude/`에 반영한다.
4. `git commit`으로 변경 이력을 남긴다(`local/`의 실제 머신 값은 커밋되지 않는다).

## 머신 종속 설정 (local override + merge)

`local/`에는 두 종류의 머신 종속 값을 둔다. 둘 다 `local/*`가 git-ignored라 이 머신에만 적용된다.

**1. settings.json 값 (merge)** — 광범위 권한이나 프록시 환경의 `HTTPS_PROXY`·`NODE_EXTRA_CA_CERTS` 같은 **이 머신에만 필요한 값**은 git에 올리지 않으면서도 **모든 디렉터리에서 전역 적용**되어야 한다. Claude Code에서 전역 적용되는 설정은 `~/.claude/settings.json` 하나뿐이므로(`~/.claude/settings.local.json`은 홈 디렉터리에서 실행할 때만 먹는 함정이다), 공통 설정과 머신 값을 sync 시점에 합쳐서 그 파일에 쓴다.

**2. 일반 파일 오버라이드 (rules·skills·최상위 파일)** — 이 머신에만 쓸 rule·skill·스크립트를 `local/`에 `home/`과 같은 구조(`local/rules/`, `local/skills/`, 최상위 파일)로 둘 수 있다. sync는 `home/`을 먼저 `~/.claude/`에 적용한 뒤, `local/`의 일반 파일로 덮어쓴다.

- **무조건 승인**: `local/`에서 오는 변경은 이 머신 전용이므로 sync 시 dry-run으로 파일 목록을 보여주고 **승인 프롬프트**를 낸다. 거부하면 local sync 전체를 건너뛴다(`home/` sync는 이미 끝난 상태).
- **중복 금지**: `home/`과 `local/`에 같은 경로가 있으면 sync를 거부한다. 공통은 `home/`, 이 머신 전용은 `local/`로 하나만 둔다.
- **삭제는 자동으로 안 함**: `local/`에서 파일을 빼면 `~/.claude/`에 잔존한다. 다음 sync에서 `home/`에도 없는 파일로 분류돼 **삭제 제안 프롬프트**가 뜨며, 승인할 때만 지운다.

**셋업** (`jq` 필요 — 없으면 `apt install jq` / `brew install jq`)

1. `local/settings.override.json.example`을 복사한다.
2. **주석을 모두 지우고** 실제 머신 종속 값을 채운다. → strict JSON이어야 한다(`jq`가 JSONC 주석을 못 읽고, `http://...` 값 안의 `//`와도 충돌한다).
3. `local/settings.override.json`으로 저장한 뒤, `jq . local/settings.override.json`으로 strict JSON인지 검증한다. (이 파일은 git-ignored라 커밋되지 않는다)

**동작**

- `claude-sync-to-home` 실행 시 `home/settings.json`(baseline) + `local/settings.override.json`(override)을 deep-merge해서 `~/.claude/settings.json`에 쓴다.
  - 객체: 키 병합 / 배열(`permissions.allow` 등): 합집합 / 스칼라: override 우선
- override가 **없으면** settings.json은 그냥 baseline 그대로 복사된다.
- `claude-diff-with-home`은 merge 결과를 기준으로 diff를 보여주므로, sync 전에 실제 반영될 내용을 확인할 수 있다.

> 머신 종속 실제 값은 `local/`에만 두고 **절대 커밋하지 말 것.** 루트 `.gitignore`가 `local/*`를 무시하고 `*.example` 템플릿만 추적한다.

## 규칙 로딩 (`home/rules/`)

`home/rules/*.md`는 `~/.claude/`로 sync되어 Claude Code가 **매 세션 자동 로드**한다. 기본값은 본문 전체가 항상 컨텍스트에 올라가는 것이므로, 특정 맥락에서만 필요한 규칙은 frontmatter로 조건부 로딩해서 컨텍스트를 아낀다.

- **전역 규칙**(frontmatter 없음): 매 세션 항상 로드. 예) `response-format.md`, `tool-usage.md`, `git-commit-guidelines.md`
- **`paths:` 스코프 규칙**: 파일 최상단 YAML frontmatter에 `paths:` glob을 적으면, 매칭되는 파일을 **읽을 때만** 본문이 로드된다(그 전엔 컨텍스트에 없음). 좁은 맥락에서만 쓰는 규칙에 적용한다.
  - `agent-instruction-files.md` → `**/AGENTS.md`, `**/CLAUDE.md` (지시 파일 작성 시)
  - `python-guidelines.md` → `**/*.py` 등 (Python 작업 시)

```markdown
---
paths:
  - "**/*.py"
---
```

- 규칙 파일 frontmatter는 **`paths:`만 지원**한다(`description`/`globs`/`alwaysApply` 등은 규칙에선 안 먹는다).
- `CLAUDE.md`의 `@import`는 lazy가 아니라 **세션 시작 시 본문을 펼치는 eager 로딩**이라 컨텍스트 절약 효과가 없다. "필요할 때만 로드"는 `paths:` frontmatter로(절차·체크리스트형이면 skill로) 처리한다.

## Output style (`home/output-styles/`)

`home/output-styles/*.md`는 `~/.claude/output-styles/`로 sync되고, 어느 것을 쓸지는 `home/settings.json`의 `outputStyle` 값으로 정한다. 현재는 [snflkd/fluent-korean](https://github.com/snflkd/fluent-korean)의 지침에 세부 동작 블록을 덧붙인 `fluent-korean` 하나를 둔다(한국어 출력 품질 교정용).

- **`rules/`와 층위가 다르다**: `rules/`는 첫 사용자 메시지 영역에 주입되지만, output style은 **시스템 프롬프트**에 `# Output Style` 절로 삽입된다. 시스템 프롬프트는 매 턴 재구성되므로 컨텍스트가 압축돼도 유지된다. 준수율이 중요한 지침은 `rules/`가 아니라 여기에 둔다.
- **`outputStyle`은 baseline에 둔다**: 모든 머신에 공통으로 적용되는 값이므로 `home/settings.json`에 두고, `~/.claude/settings.json`을 직접 고치지 않는다(다음 sync에서 덮어써진다).
- **디렉터리 안의 md는 전부 개별 스타일로 로드된다**: 조각 파일이나 작성 중인 메모를 이 디렉터리에 두면 안 된다. 완성본만 둔다.
- **이름이 어긋나면 조용히 기본 스타일로 되돌아간다**: `outputStyle` 값은 frontmatter의 `name`(없으면 파일명)과 일치해야 하는데, 어긋나도 경고가 없다. sync 후 `/config` → Output style 항목을 **열어서** 목록에 description과 함께 뜨는지 확인한다(값 칸의 문자열만으로는 로드 여부를 알 수 없다).
- **적용에는 새 세션이 필요하다**: 시스템 프롬프트 층위라 `/clear` 또는 새 세션부터 반영된다.
- **프로젝트 설정이 사용자 설정보다 우선한다**: 특정 프로젝트에서만 적용되지 않으면 그 프로젝트의 `.claude/settings.json`·`.claude/settings.local.json`을 먼저 확인한다(`/config`에서 고른 값은 후자에 기록된다).
- **이 문서만 한국어로 유지한다**: `rules/`·`skills/`는 영어로 통일하지만, output style은 조사·어미 같은 한국어 형태론 자체를 다루고 조항마다 한국어 예시가 붙어 있어 번역하면 정밀도가 떨어진다. 원본 본문도 요약·변형을 만류하고 있고, 상류와 대조하려면 원문이어야 한다.
- **상류 갱신은 수동으로 반영한다**: 원본 저장소를 pull한 뒤 diff를 확인하고, 세부 동작 블록을 유지한 채 손으로 옮긴다. 모든 응답을 좌우하는 지침이므로 자동 덮어쓰기를 피한다.

## Skill 작성 가이드

새 skill은 반드시 `reference-skills/`의 공식 예제를 참고해서 만든다.

- skill 구조·포맷: `reference-skills/spec/`, `reference-skills/template/`
- 실제 예시: `reference-skills/skills/` 하위
- `reference-skills/`는 참고 전용 submodule이므로 직접 수정하지 않는다.
