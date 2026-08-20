#!/bin/bash
# Claude Code statusline.
#
# Line 1 mirrors ~/.bashrc PS1 (plus the session name when known):
#   PS1='${debian_chroot:+($debian_chroot)}\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\w\[\033[00m\]\$ '
# Line 2: [model effort] bar % context │ used · out (session totals) │ cost
#
# Two different token numbers, deliberately kept apart:
#   - context (next to the bar) is one request's size. It drops on compact.
#     That is what the JSON's total_input_tokens is — the latest response's
#     input + cache_read + cache_creation, not a session total.
#   - used / out are session totals, summed from the transcript since the JSON
#     carries no cumulative counter. "used" = non-cached input (fresh input +
#     cache writes) + output, i.e. cache reads excluded — the same definition
#     as Codex's `used-tokens` status item, so the two status lines agree.
#     "out" = output tokens (thinking included).
#
# Cost is also computed from the transcript (tokens x list price), not from
# the JSON's cost.total_cost_usd: that value is per-process and resets to 0
# on --resume (anthropics/claude-code#13088), while the transcript keeps the
# whole session. The JSON value is only a fallback when the transcript is
# unreadable.
#
# Shares its layout with ~/.claude/statusline-internal.sh (the claude-internal
# variant); that one resolves the real litellm backend model and drops cost.
#
# Reads the session JSON on stdin. See `claude --debug` if it stops rendering.

input=$(cat)

# Split on U+001F, not tab: tab is an IFS whitespace character, so consecutive
# empty fields (common before the first API response) would collapse and shift
# every value one slot to the left.
IFS=$'\037' read -r cwd model pct tok_in ctx_size effort cost rl5 rl7 sid transcript sname < <(
  printf '%s' "$input" | jq -r '
    [ .workspace.current_dir // .cwd // "",
      .model.display_name // "?",
      (.context_window.used_percentage // (100 - (.context_window.remaining_percentage // 100))),
      (.context_window.total_input_tokens // 0),
      (.context_window.context_window_size // ""),
      (.effort.level // ""),
      (.cost.total_cost_usd // 0),
      (.rate_limits.five_hour.used_percentage // ""),
      (.rate_limits.seven_day.used_percentage // ""),
      (.session_id // "nosession"),
      (.transcript_path // ""),
      (.session_name // .agent.name // "")
    ] | map(tostring) | join("\u001f")'
)

[ -z "$cwd" ] && cwd=$(pwd)
pct=$(printf '%.0f' "${pct:-0}" 2>/dev/null || echo 0)

# --- session totals (incremental transcript scan) ---------------------------
# One response is written as several lines (one per content block) and every
# line repeats the same usage, so only count when message.id changes. Identical
# ids are always adjacent, which makes this a plain O(n) scan — no sorting.
# A full reparse costs 54ms on an 8.6MB transcript; resuming from the last
# offset avoids paying that on every render. Only process when the file ends on
# a newline, so a half-written line is never counted as a whole one.
cum_used=0; cum_out=0; cum_cost=0
if [ -n "$transcript" ] && [ -r "$transcript" ]; then
  ccache="/tmp/statusline-cum-${sid}.cache"
  # Cache line: 2|offset|last_id|used|out|cost. The leading "2" is a format
  # version: the previous format (offset|last_id|in|out|cost) has the same
  # field count but stores Σ in (cache reads included) where used now lives,
  # so a missing/other version rescans from zero instead of mixing the two.
  cver=""; coff=0; clast=""
  [ -f "$ccache" ] && IFS='|' read -r cver coff clast cum_used cum_out cum_cost < "$ccache"
  [ "$cver" = "2" ] && [ -n "$cum_cost" ] || { coff=0; clast=""; cum_used=0; cum_out=0; cum_cost=0; }
  fsize=$(stat -c %s "$transcript" 2>/dev/null || echo 0)
  (( ${coff:-0} > fsize )) && { coff=0; clast=""; cum_used=0; cum_out=0; cum_cost=0; }
  if (( fsize > ${coff:-0} )) && [ -z "$(tail -c 1 "$transcript")" ]; then
    # Fields: id|model|input|cache_read|cache_5m|cache_1h|output ("|" never
    # appears in ids or model names). used = input + cache_5m + cache_1h +
    # output (cache_read left out). Cost accumulates in integer microdollars
    # (tokens x $/MTok): every current model prices output at 5x input, so one
    # input rate per family is enough. Cache read bills at 0.1x input, cache
    # writes at 1.25x (5m) / 2x (1h). Unknown models (incl. <synthetic>) count
    # tokens but add no cost.
    read -r add_used add_out add_cost clast < <(
      tail -c "+$(( coff + 1 ))" "$transcript" 2>/dev/null \
        | jq -r 'select(.message.usage) | .message as $m
            | [ $m.id, ($m.model // ""),
                ($m.usage.input_tokens // 0),
                ($m.usage.cache_read_input_tokens // 0),
                ($m.usage.cache_creation.ephemeral_5m_input_tokens // $m.usage.cache_creation_input_tokens // 0),
                ($m.usage.cache_creation.ephemeral_1h_input_tokens // 0),
                ($m.usage.output_tokens // 0)
              ] | map(tostring) | join("|")' 2>/dev/null \
        | awk -F'|' -v p="$clast" '
            function rin(m) {
              if (m ~ /^claude-(fable|mythos)/) return 10
              if (m ~ /^claude-opus-4-[01]/)   return 15
              if (m ~ /^claude-opus/)          return 5
              if (m ~ /^claude-sonnet/)        return 3
              if (m ~ /^claude-haiku/)         return 1
              return 0
            }
            $1!=p {
              u += $3 + $5 + $6 + $7; o += $7
              r = rin($2)
              c += ($3 + 0.1*$4 + 1.25*$5 + 2*$6) * r + $7 * r * 5
              p = $1
            }
            END { print u+0, o+0, sprintf("%.0f", c), p }'
    )
    cum_used=$(( ${cum_used:-0} + ${add_used:-0} ))
    cum_out=$(( ${cum_out:-0} + ${add_out:-0} ))
    cum_cost=$(( ${cum_cost:-0} + ${add_cost:-0} ))
    tmp=$(mktemp "${ccache}.XXXXXX" 2>/dev/null)
    printf '2|%s|%s|%s|%s|%s' "$fsize" "$clast" "$cum_used" "$cum_out" "$cum_cost" > "$tmp" 2>/dev/null \
      && mv -f "$tmp" "$ccache" 2>/dev/null || rm -f "$tmp" 2>/dev/null
  fi
fi

# 15.5k / 1M style so the line stays narrow. Plain shell arithmetic rather than
# awk: this runs on every render, so each avoided process is felt.
human() {
  local t=${1:-0} i f u
  [[ $t =~ ^[0-9]+$ ]] || t=0
  if   (( t >= 1000000 )); then i=$(( t / 1000000 )); f=$(( (t % 1000000) / 100000 )); u=M
  elif (( t >= 1000 ));    then i=$(( t / 1000 ));    f=$(( (t % 1000) / 100 ));       u=k
  else printf '%d' "$t"; return
  fi
  if (( f > 0 )); then printf '%d.%d%s' "$i" "$f" "$u"; else printf '%d%s' "$i" "$u"; fi
}

# --- line 1: PS1 clone ------------------------------------------------------
case "$cwd" in
  "$HOME")   path_display="~" ;;
  "$HOME"/*) path_display="~${cwd#"$HOME"}" ;;
  *)         path_display="$cwd" ;;
esac

line1="${debian_chroot:+($debian_chroot)}\033[01;32m$(whoami)@$(hostname -s)\033[00m:\033[01;34m${path_display}\033[00m"

# Session name: the local session registry holds the addressable peer name —
# what ListAgents shows and SendMessage targets (e.g. "dir-aa"; changes on
# resume since it is keyed to the process). The JSON's session_name is only a
# display title (/rename or AI-generated), not the address, so it is kept as
# a fallback for when the undocumented registry misses.
if [ "$sid" != "nosession" ]; then
  sfile=$(grep -ls "$sid" "$HOME/.claude/sessions/"*.json 2>/dev/null | head -1)
  [ -n "$sfile" ] && rname=$(jq -r '.name // empty' "$sfile" 2>/dev/null)
fi
[ -n "$rname" ] && sname=$rname
[ -n "$sname" ] && line1="${line1} \033[02m(${sname})\033[00m"

# --- line 2: session telemetry ---------------------------------------------
sep="\033[02m│\033[00m"

# "Opus 5 (1M context)" is too wide for a status bar.
model=${model/ (1M context)/ 1M}

# Effort rides inside the model bracket; omitted when the API sends none.
if [ -n "$effort" ]; then
  model_tag="\033[00;36m[${model} \033[02m${effort}\033[00;36m]\033[00m"
else
  model_tag="\033[00;36m[${model}]\033[00m"
fi

# Green while there is room, amber past the halfway mark, red near the wall.
if   (( pct >= 90 )); then bar_color="00;31"
elif (( pct >= 70 )); then bar_color="00;33"
else                       bar_color="00;32"
fi

bar_width=10
filled=$(( pct * bar_width / 100 ))
(( filled > bar_width )) && filled=$bar_width
(( filled < 0 )) && filled=0
empty=$(( bar_width - filled ))
bar=""
(( filled > 0 )) && printf -v _f "%${filled}s" && bar="${_f// /█}"
(( empty  > 0 )) && printf -v _e "%${empty}s"  && bar="${bar}${_e// /░}"

ctx="\033[${bar_color}m${bar}\033[00m ${pct}% \033[02m$(human "$tok_in")/$(human "$ctx_size")\033[00m"
# Same shape as Codex's status line: "<n> used · <n> out".
tokens="$(human "$cum_used") \033[02mused\033[00m · $(human "$cum_out") \033[02mout\033[00m"
# Prefer the transcript-derived cumulative cost: the JSON value is
# per-process and resets to $0 on resume.
if [ -n "$transcript" ] && [ -r "$transcript" ]; then
  spend_txt="$(( cum_cost / 1000000 )).$(printf '%02d' $(( (cum_cost % 1000000) / 10000 )))"
else
  spend_txt=$(printf '%.2f' "${cost:-0}" 2>/dev/null || printf '0.00')
fi
spend="\033[00;35m\$${spend_txt}\033[00m"

line2="${model_tag} ${ctx} ${sep} ${tokens} ${sep} ${spend}"

# Absent on this account today, but rendered automatically if the API starts
# reporting subscription rate limits. Truncated to whole percent: the API
# sends raw floats (e.g. 7.000000001).
limits=""
[ -n "$rl5" ] && { rl5=${rl5%%.*}; rl5=${rl5:-0}; }
[ -n "$rl7" ] && { rl7=${rl7%%.*}; rl7=${rl7:-0}; }
[ -n "$rl5" ] && limits="${limits} \033[02m5h\033[00m ${rl5}%"
[ -n "$rl7" ] && limits="${limits} \033[02m7d\033[00m ${rl7}%"
[ -n "$limits" ] && line2="${line2} ${sep}${limits}"

printf "%b\n%b" "$line1" "$line2"
