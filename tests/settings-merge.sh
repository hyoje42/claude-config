#!/bin/bash
#
# claude-merge-settings 단위 테스트.
#
# 임시 디렉터리의 JSON 고정물로 merge 도구를 직접 호출해 다음을 검증한다:
#   - 객체는 키 단위로 재귀 deep-merge된다(중첩 깊이와 무관하게 형제 키 보존)
#   - 스칼라는 override가 이긴다
#   - 배열은 union이다: baseline 순서 유지, override 전용 항목만 뒤에 추가, 중복 제거
#   - 타입이 다르면 override가 통째로 이긴다
#   - override가 없거나·파일이 없거나·객체가 아니거나·잘못된 JSON이면 baseline을 그대로 내보낸다(exit 0)
#   - baseline이 없거나 객체가 아니면 exit 1이고 stdout은 비어 있다
#
# sync-home.sh는 merge 결과를 merge 도구 자신의 출력과 비교하므로(동어반복), merge 의미론은
# 여기서 고정한다. 실제 ~/.claude는 건드리지 않는다.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
MERGE="$REPO/claude-merge-settings"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf -- "$TEST_ROOT"' EXIT

fail() {
    echo "실패: $*" >&2
    exit 1
}
# check <json-file> <jq-filter> <message>: 필터가 true가 아니면 실패한다.
check() { jq -e "$2" "$1" >/dev/null 2>&1 || fail "$3"; }

BASE="$TEST_ROOT/base.json"
OVERRIDE="$TEST_ROOT/override.json"
OUT="$TEST_ROOT/out.json"
ERR="$TEST_ROOT/err.txt"

###############################################################################
echo "[1] deep-merge: 중첩 객체·스칼라 우선순위·배열 union·타입 불일치"
cat > "$BASE" <<'JSON'
{
  "outputStyle": "fluent-korean",
  "model": "base-model",
  "env": { "A": "base-a", "NESTED": { "KEEP": "1", "DEEP": { "p": 1 } } },
  "permissions": {
    "allow": ["Bash(git:*)", "Read", "Bash(ls:*)"],
    "deny": ["Bash(rm:*)"],
    "defaultMode": "default"
  },
  "arrayToScalar": [1, 2],
  "objectToArray": { "k": "v" },
  "baseOnly": true
}
JSON
cat > "$OVERRIDE" <<'JSON'
{
  "model": "override-model",
  "env": { "B": "override-b", "NESTED": { "DEEP": { "q": 2 }, "ADDED": "2" } },
  "permissions": {
    "allow": ["Bash(ls:*)", "Bash(foo:*)", "Read", "Bash(bar:*)"],
    "defaultMode": "acceptEdits"
  },
  "arrayToScalar": "scalar",
  "objectToArray": ["x"],
  "overrideOnly": { "new": "key" }
}
JSON
"$MERGE" "$BASE" "$OVERRIDE" > "$OUT" 2>"$ERR" || fail "정상 입력에서 merge가 실패했습니다: $(cat "$ERR")"
[ ! -s "$ERR" ]                                             || fail "정상 입력에서 stderr에 출력이 있습니다: $(cat "$ERR")"
check "$OUT" 'type == "object"'                             "결과가 JSON 객체가 아닙니다."
# 스칼라: override 우선, baseline 전용 키 보존
check "$OUT" '.model == "override-model"'                   "스칼라가 override 값으로 바뀌지 않았습니다."
check "$OUT" '.outputStyle == "fluent-korean"'              "baseline 전용 스칼라가 사라졌습니다."
check "$OUT" '.baseOnly == true'                            "baseline 전용 키가 사라졌습니다."
check "$OUT" '.overrideOnly == {"new":"key"}'               "override 전용 키가 추가되지 않았습니다."
# 중첩 객체: 깊이 1~3에서 형제 키 보존 + 추가 (jq $a/$b 바인딩 회귀 방지)
check "$OUT" '.env.A == "base-a" and .env.B == "override-b"'            "env 1단계 merge가 틀렸습니다."
check "$OUT" '.env.NESTED.KEEP == "1" and .env.NESTED.ADDED == "2"'      "env 2단계 형제 키가 보존·추가되지 않았습니다."
check "$OUT" '.env.NESTED.DEEP == {"p":1,"q":2}'                          "env 3단계 deep-merge가 틀렸습니다."
check "$OUT" '.permissions.deny == ["Bash(rm:*)"]'                        "override에 없는 중첩 배열이 사라졌습니다."
check "$OUT" '.permissions.defaultMode == "acceptEdits"'                  "중첩 스칼라가 override 값으로 바뀌지 않았습니다."
# 배열 union: baseline 순서 유지, override 전용 항목만 baseline 뒤에 override 순서로 추가, 중복 없음
check "$OUT" '.permissions.allow == ["Bash(git:*)","Read","Bash(ls:*)","Bash(foo:*)","Bash(bar:*)"]' \
    "배열 union의 순서·중복 제거가 틀렸습니다: $(jq -c '.permissions.allow' "$OUT")"
# 타입 불일치: override가 통째로 이김
check "$OUT" '.arrayToScalar == "scalar"'                   "배열→스칼라 타입 불일치에서 override가 이기지 않았습니다."
check "$OUT" '.objectToArray == ["x"]'                      "객체→배열 타입 불일치에서 override가 이기지 않았습니다."
# 멱등: 결과를 다시 같은 override와 merge해도 동일
"$MERGE" "$OUT" "$OVERRIDE" > "$TEST_ROOT/out2.json"
[ "$(jq -S . "$OUT")" = "$(jq -S . "$TEST_ROOT/out2.json")" ] || fail "같은 override를 다시 merge했을 때 결과가 달라졌습니다."

###############################################################################
echo "[2] override 없음·파일 없음: baseline 그대로(exit 0)"
"$MERGE" "$BASE" > "$OUT" 2>"$ERR"                          || fail "override 인자 없이 merge가 실패했습니다."
[ "$(jq -S . "$OUT")" = "$(jq -S . "$BASE")" ]              || fail "override 인자 없을 때 baseline이 그대로 나오지 않았습니다."
[ ! -s "$ERR" ]                                             || fail "override 인자 없을 때 경고가 출력됐습니다: $(cat "$ERR")"
"$MERGE" "$BASE" "$TEST_ROOT/missing.json" > "$OUT" 2>"$ERR" || fail "override 파일이 없을 때 merge가 실패했습니다."
[ "$(jq -S . "$OUT")" = "$(jq -S . "$BASE")" ]              || fail "override 파일이 없을 때 baseline이 그대로 나오지 않았습니다."
[ ! -s "$ERR" ]                                             || fail "override 파일이 없을 때 경고가 출력됐습니다(없는 파일은 조용히 무시해야 함)."

###############################################################################
echo "[3] 무효 override(비객체·JSONC·빈 파일): 경고 후 baseline 그대로(exit 0)"
for bad in '["not","an","object"]' '{ // comment breaks strict json' '' '"just a string"'; do
    printf '%s' "$bad" > "$OVERRIDE"
    "$MERGE" "$BASE" "$OVERRIDE" > "$OUT" 2>"$ERR"          || fail "무효 override($bad)에서 merge가 실패했습니다(무시하고 baseline을 내야 함)."
    [ "$(jq -S . "$OUT")" = "$(jq -S . "$BASE")" ]          || fail "무효 override($bad)에서 baseline이 그대로 나오지 않았습니다."
    if [ -n "$bad" ]; then
        [ -s "$ERR" ]                                        || fail "무효 override($bad)를 무시했는데 경고가 없습니다."
    fi
done

###############################################################################
echo "[4] baseline 오류(없음·비객체·JSONC): exit 1, stdout 비어 있음"
printf '{"k":1}' > "$OVERRIDE"
set +e
"$MERGE" "$TEST_ROOT/no-such-base.json" "$OVERRIDE" > "$OUT" 2>"$ERR"; rc=$?
set -e
[ "$rc" -eq 1 ]                                             || fail "baseline 파일이 없는데 exit 1이 아닙니다(exit $rc)."
[ ! -s "$OUT" ]                                             || fail "baseline 파일이 없는데 stdout에 출력이 있습니다."
[ -s "$ERR" ]                                               || fail "baseline 파일이 없는데 오류 메시지가 없습니다."
for bad in '[1,2]' '{ // jsonc' 'null'; do
    printf '%s' "$bad" > "$BASE"
    set +e
    "$MERGE" "$BASE" "$OVERRIDE" > "$OUT" 2>"$ERR"; rc=$?
    set -e
    [ "$rc" -eq 1 ]                                         || fail "baseline($bad)이 객체가 아닌데 exit 1이 아닙니다(exit $rc)."
    [ ! -s "$OUT" ]                                         || fail "baseline($bad)이 객체가 아닌데 stdout에 출력이 있습니다."
done

###############################################################################
echo "[5] 인자 없음: usage 오류로 종료, stdout 비어 있음"
set +e
"$MERGE" > "$OUT" 2>"$ERR"; rc=$?
set -e
[ "$rc" -ne 0 ]                                             || fail "인자 없이 실행했는데 성공으로 종료했습니다."
[ ! -s "$OUT" ]                                             || fail "인자 없이 실행했는데 stdout에 출력이 있습니다."

echo "통과: claude-merge-settings의 deep-merge·배열 union·override 무시·오류 종료 코드를 확인했습니다."
