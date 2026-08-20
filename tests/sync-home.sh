#!/bin/bash
#
# claude-diff-with-home / claude-sync-to-home 회귀 테스트.
#
# 임시 HOME과 repo 사본(fixture)에서 dry-run(diff)과 sync를 실행해 다음을 검증한다:
#   - dry-run은 ~/.claude에 아무것도 쓰지 않는다
#   - dry-run이 언급한 경로(변경/신규/local/고아)가 sync에서 그대로 적용된다
#   - sync 직후 diff는 "차이 없음", sync는 "변경 사항 없음"(멱등)
#   - 무효 override·home/local 중복은 dry-run이 통과시키고 sync가 거부한다
#   - 승인 프롬프트에 n을 주면 local/고아는 건드리지 않는다
#
# 단언은 파일 시스템 결과·종료 코드·경로 언급 여부 위주로 둔다. 안내 문구·요약
# 포맷·프롬프트 개수가 바뀌어도 깨지지 않게 하기 위함이다(동작이 바뀔 때만 깨진다).
# 실제 ~/.claude는 건드리지 않는다.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT

fail() {
    echo "실패: $*" >&2
    exit 1
}
has()   { grep -Fq -- "$2" <<<"$1"; }    # has <text> <substring>
lacks() { ! grep -Fq -- "$2" <<<"$1"; }

# 디렉터리 전체를 경로+내용 해시로 스냅샷한다(변경 없음 판정용).
snapshot() {
    (cd "$1" && find . -type f | sort | while read -r f; do md5sum "$f"; done)
}

# 시나리오마다 새 fixture repo + HOME을 만든다. git 메타·백업·실제 local 값은 복사하지 않는다.
new_fixture() {  # new_fixture <name>  → FX(repo) / HOME_DIR / H(~/.claude)
    FX="$TEST_ROOT/$1/repo"
    HOME_DIR="$TEST_ROOT/$1/home"
    H="$HOME_DIR/.claude"
    mkdir -p "$FX" "$H"
    rsync -a --exclude='/.git' --exclude='/_backup' --exclude='/local/*' "$REPO/" "$FX/"
    mkdir -p "$FX/local"
    cp "$REPO"/local/*.example "$FX/local/" 2>/dev/null || true
}
# rsync는 크기+mtime으로 같은 파일을 판정하므로, 미리 둔 HOME 파일은 과거 mtime으로 둔다.
age_home() { find "$HOME_DIR" -type f -exec touch -d '2020-01-01 00:00:00' {} +; }

run_diff() { HOME="$HOME_DIR" "$FX/claude-diff-with-home" 2>&1; }
# run_sync <y|n>: 모든 승인 프롬프트에 같은 답을 넉넉히 흘려 넣는다(프롬프트 수에 의존하지 않음).
run_sync() { printf "$1\n%.0s" {1..20} | HOME="$HOME_DIR" "$FX/claude-sync-to-home" 2>&1; }
# 실패가 기대되는 sync: 종료 코드를 RC에, 출력을 OUT에 담는다.
run_sync_rc() { set +e; OUT="$(run_sync "$1")"; RC=$?; set -e; }

###############################################################################
echo "[1] 전체: 변경·신규·local·고아·override merge → dry-run 언급 = sync 적용"
new_fixture s1
mkdir -p "$H/rules" "$H/skills/foo" "$H/output-styles"
cp "$FX/home/rules/tool-usage.md" "$H/rules/"; echo "stale line" >> "$H/rules/tool-usage.md"   # 변경
cp "$FX/home/rules/python-guidelines.md" "$H/rules/"                                          # 동일
echo orphan > "$H/rules/zzz-orphan.md"                                                         # 고아(rules)
echo orphan > "$H/skills/foo/SKILL.md"                                                         # 고아(skills)
echo orphan > "$H/output-styles/old.md"                                                        # 고아(output-styles)
echo '{"old":true}' > "$H/settings.json"                                                       # stale settings
echo unrelated > "$H/unrelated.json"                                                           # 관리 밖 파일
echo '{"x":1}' > "$H/settings.local.json"                                                      # sync가 건드리면 안 됨
echo old-local > "$H/rules/local-only.md"                                                      # local 변경 대상
mkdir -p "$FX/local/rules" "$FX/local/agents"
echo '{"env":{"HTTPS_PROXY":"http://p:1"},"permissions":{"allow":["Bash(foo:*)"]}}' > "$FX/local/settings.override.json"
echo new-local > "$FX/local/rules/local-only.md"                                               # local 변경
echo new-agent > "$FX/local/agents/new.md"                                                     # local 신규
echo '{"stray":1}' > "$FX/home/settings.local.json"                                            # 떠도는 파일: 항상 제외
age_home

before="$(snapshot "$HOME_DIR")"
out="$(run_diff)"
[ "$(snapshot "$HOME_DIR")" = "$before" ]  || fail "dry-run이 HOME을 변경했습니다."
for p in rules/tool-usage.md settings.json rules/response-format.md rules/local-only.md agents/new.md \
         rules/zzz-orphan.md skills/foo/SKILL.md output-styles/old.md; do
    has "$out" "$p" || fail "dry-run이 $p 를 언급하지 않았습니다."
done
has "$out" 'http://p:1'                    || fail "dry-run의 settings.json 내용에 override 값이 없습니다(merge 결과로 비교해야 함)."
lacks "$out" "rules/python-guidelines.md"  || fail "동일한 파일을 변경으로 언급했습니다."
lacks "$out" "settings.local.json"         || fail "sync가 제외하는 settings.local.json을 dry-run이 언급했습니다."
lacks "$out" "unrelated.json"              || fail "관리 밖 파일을 언급했습니다."

run_sync y >/dev/null
cmp -s "$H/rules/tool-usage.md" "$FX/home/rules/tool-usage.md"          || fail "변경 파일이 갱신되지 않았습니다."
cmp -s "$H/rules/response-format.md" "$FX/home/rules/response-format.md" || fail "신규 파일이 설치되지 않았습니다."
"$FX/claude-merge-settings" "$FX/home/settings.json" "$FX/local/settings.override.json" > "$TEST_ROOT/s1-merged.json"
cmp -s "$H/settings.json" "$TEST_ROOT/s1-merged.json"                  || fail "settings.json이 merge 결과와 다릅니다."
[ "$(cat "$H/rules/local-only.md")" = "new-local" ]                     || fail "local 변경 파일이 적용되지 않았습니다."
[ "$(cat "$H/agents/new.md")" = "new-agent" ]                           || fail "local 신규 파일이 설치되지 않았습니다."
[ ! -e "$H/rules/zzz-orphan.md" ]                                       || fail "rules 고아 파일이 삭제되지 않았습니다."
[ ! -e "$H/skills/foo" ]                                                || fail "skills 고아 디렉터리가 정리되지 않았습니다."
[ ! -e "$H/output-styles/old.md" ]                                      || fail "output-styles 고아 파일이 삭제되지 않았습니다."
[ "$(cat "$H/unrelated.json")" = "unrelated" ]                          || fail "관리 밖 파일이 손상됐습니다."
[ "$(cat "$H/settings.local.json")" = '{"x":1}' ]                       || fail "settings.local.json이 덮어써졌습니다."
find "$FX/_backup" -path '*/rules/zzz-orphan.md' -print -quit | grep -q .  || fail "삭제한 고아 파일의 백업이 없습니다."
find "$FX/_backup" -path '*/rules/local-only.md' -print -quit | grep -q .  || fail "local로 덮어쓴 파일의 백업이 없습니다."
[ "$(cat "$(find "$FX/_backup" -maxdepth 2 -name settings.json -print -quit)")" = '{"old":true}' ] \
                                                                        || fail "settings.json 이전 값 백업이 없습니다."

out="$(run_diff)"; has "$out" "차이 없음"          || fail "sync 직후 dry-run이 깨끗하지 않습니다."
out="$(run_sync y)"; has "$out" "변경 사항 없음"   || fail "sync 직후 재실행이 멱등하지 않습니다."
[ ! -e "$H/skills/foo" ] && [ "$(cat "$H/rules/local-only.md")" = "new-local" ] \
                                                   || fail "재실행이 상태를 바꿨습니다."

###############################################################################
echo "[2] 승인 거부(n): local·고아는 그대로, home/은 적용"
new_fixture s2
mkdir -p "$H/rules"
echo orphan > "$H/rules/zzz-orphan.md"
echo old-local > "$H/rules/loc.md"
age_home
mkdir -p "$FX/local/rules"; echo new-local > "$FX/local/rules/loc.md"
run_sync n >/dev/null
[ "$(cat "$H/rules/loc.md")" = "old-local" ]   || fail "거부했는데 local 파일이 적용됐습니다."
[ -e "$H/rules/zzz-orphan.md" ]                || fail "거부했는데 고아 파일이 삭제됐습니다."
[ -f "$H/rules/tool-usage.md" ]                || fail "home/ 파일이 설치되지 않았습니다."

###############################################################################
echo "[3] 무효 override: dry-run은 계속 진행, sync는 거부하고 아무것도 쓰지 않음"
new_fixture s3
echo '{ // not strict json' > "$FX/local/settings.override.json"
before="$(snapshot "$HOME_DIR")"
out="$(run_diff)"                              || fail "무효 override에서 dry-run이 실패했습니다(읽기 전용이라 계속 진행해야 함)."
has "$out" "rules/tool-usage.md"               || fail "무효 override에서 dry-run이 일반 파일 비교를 건너뛰었습니다."
run_sync_rc y
[ "$RC" -eq 1 ]                                || fail "무효 override인데 sync가 거부하지 않았습니다(exit $RC)."
[ "$(snapshot "$HOME_DIR")" = "$before" ]      || fail "거부된 sync가 HOME을 변경했습니다."
[ ! -d "$FX/_backup" ]                         || fail "거부된 sync가 백업을 만들었습니다."

###############################################################################
echo "[4] home/과 local/ 경로 중복: dry-run은 언급, sync는 거부"
new_fixture s4
mkdir -p "$FX/local/rules"; echo dup > "$FX/local/rules/tool-usage.md"
out="$(run_diff)"; has "$out" "rules/tool-usage.md" || fail "중복 경로를 언급하지 않았습니다."
run_sync_rc y
[ "$RC" -eq 1 ]                                || fail "중복인데 sync가 거부하지 않았습니다(exit $RC)."
has "$OUT" "rules/tool-usage.md"               || fail "거부 사유에 중복 경로가 없습니다."
[ -z "$(ls -A "$H")" ]                         || fail "거부된 sync가 HOME에 파일을 썼습니다."

###############################################################################
echo "[5] override 없음: settings.json은 baseline 그대로"
new_fixture s5
run_sync y >/dev/null
cmp -s "$H/settings.json" "$FX/home/settings.json" || fail "override 없이 settings.json이 baseline과 다릅니다."
[ ! -e "$H/settings.local.json" ]              || fail "repo에 없는 settings.local.json이 생성됐습니다."

###############################################################################
echo "[6] override만 변경: rsync는 변경 없음이어도 merge가 적용된다"
new_fixture s6
run_sync y >/dev/null
echo '{"env":{"ONLY":"1"}}' > "$FX/local/settings.override.json"
out="$(run_diff)"
has "$out" "settings.json"                     || fail "override 변경을 dry-run이 감지하지 못했습니다."
lacks "$out" "rules/"                          || fail "override만 바꿨는데 다른 파일을 언급했습니다."
run_sync y >/dev/null
jq -e '.env.ONLY == "1"' "$H/settings.json" >/dev/null || fail "merge 결과에 override 값이 없습니다."
out="$(run_sync y)"; has "$out" "변경 사항 없음" || fail "override 적용 후 재실행이 멱등하지 않습니다."

###############################################################################
echo "[7] 래퍼/옵션: diff = sync --dry-run, 알 수 없는 옵션은 exit 2"
new_fixture s7
a="$(run_diff)"; b="$(HOME="$HOME_DIR" "$FX/claude-sync-to-home" --dry-run 2>&1)"
[ "$a" = "$b" ]                                || fail "claude-diff-with-home과 --dry-run 출력이 다릅니다."
set +e; HOME="$HOME_DIR" "$FX/claude-sync-to-home" --bogus >/dev/null 2>&1; rc=$?; set -e
[ "$rc" -eq 2 ]                                || fail "알 수 없는 옵션이 exit 2가 아닙니다(exit $rc)."
[ -z "$(ls -A "$H")" ]                         || fail "dry-run/옵션 오류가 HOME에 파일을 썼습니다."

echo "통과: claude diff/sync의 미리보기·적용·멱등성·거부 경로를 확인했습니다."
