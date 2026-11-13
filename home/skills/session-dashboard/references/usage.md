# Dashboard operations

## Scope and prerequisites

Resolve `scripts/dashboard.py` from this skill's actual location. Installed skills normally live at `~/.claude/skills/session-dashboard`; the required parser must be its sibling at `../inspect-session/scripts/session_digest.py`. A missing or incompatible dependency produces a Korean error. Report that dependency and restore the matching `inspect-session` through the user's approved skill installation workflow; do not substitute a parser or install unrelated packages. Repository copies can run directly when both siblings exist.

The runtime uses Python's standard library, local HTML/CSS/JavaScript, and no model API, external assets, or API key. Follow the workspace's Python environment rule and use `-B` to avoid caches. Put **global options before the subcommand**. Use `--help` for complete options and bounds.

By default, the tool home is `CLAUDE_CONFIG_DIR` or `~/.claude`; `--home PATH` overrides only the source home, not the skill location. The current Git root (including worktree root), or current directory outside Git, sets the project. Other projects and nested repositories are excluded. Main transcripts are read only from `projects/*/*.jsonl` (also `.jsonl.gz`); nested subagent files are excluded. A session belongs to the project of its first recorded cwd, where it started; later `cd` commands that move the recorded cwd do not reassign it. The escaped project-directory name does not establish a missing cwd. The default window is 24 hours and 20 sessions; subagents and the known calling session are excluded.

- Repeat `--project PATH` to combine projects. Paths are interpreted as the roots supplied.
- Repeat `--session ID` to select explicit sessions outside the project/window/count limits. A unique prefix works; ambiguous prefixes fail with candidate IDs. Self and subagent exclusion still apply.
- Copy the observer ID substituted into the invoking `SKILL.md` from `${CLAUDE_SESSION_ID}` and pass it as a literal `--self` value. The helper deliberately ignores any shell `CLAUDE_SESSION_ID` environment variable. If the skill substitution is missing, blank, or unresolved, omit `--self` (or pass the unresolved value literally) and disclose the self-exclusion warning; never guess an ID. `--include-self` requires a user request to include the observer.
- Collection and discovery have separate intervals. Collection reuses unchanged files; discovery also notices renamed titles and new sessions. Browser refresh does not force discovery or create a summary.

The selected options determine the default private runtime directory. Keep **all global options identical** across input, import, start, status, stop, and export so they share the summary store and server. A custom `--runtime-dir` must be user-owned with mode `0700`; incompatible selections cannot reuse its running server. Runtime files and HTML exports use mode `0600`. Separate dashboards should use separate runtimes.

## Create, summarize, and start

For an installed skill, a Bash command setup can be:

```bash
dashboard_skill="$HOME/.claude/skills/session-dashboard"
dashboard_options=(--self '${CLAUDE_SESSION_ID}')
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" summary-input
```

Before running, replace the single-quoted observer placeholder with the actual value supplied in the invoking skill. Keeping an unresolved placeholder single-quoted produces an honest unconfirmed-self warning; expanding it through the shell could accidentally select an unrelated environment value. Resolve `dashboard_skill` from the actual `${CLAUDE_SKILL_DIR}` value if installed elsewhere. When the user supplied another project or specific sessions, replace the options accordingly. For the default Git-root behavior, omit `--project` rather than passing a subdirectory. Retain the returned `runtime_dir` from `start` for troubleshooting, together with the options used.

`summary-input` returns `{"schema":1,"inputs":[...],"warnings":[...]}`. Each immutable input includes `session_id`, `snapshot_id`, `sequence`, `issued_at`, `source_revision`, `title`, `recorded_turn`, and sanitized `evidence`. Each evidence event has `id`, `kind`, `timestamp`, and `text`. The bounded evidence can omit earlier requests, recent details, or long text. Read its actual content; a title alone cannot establish the goal.

For **each input**, the calling agent writes one JSON object:

```json
{
  "session_id": "COPY_FROM_INPUT",
  "snapshot_id": "COPY_FROM_INPUT",
  "fields": {
    "goal": [{"text": "검색 결과의 정렬 오류를 수정합니다.", "refs": ["12"]}],
    "completed": [{"text": "동일한 시각의 결과를 구분하는 정렬 조건을 추가했습니다.", "refs": ["18", "21"]}],
    "current": [],
    "remaining": [{"text": "사용자가 제시한 재현 사례로 결과를 확인해야 합니다.", "refs": ["12", "21"]}],
    "attention": [],
    "decisions": []
  }
}
```

The IDs and claims above are illustrative: replace them with that input's actual IDs and supported Korean statements. Each field is an array of `{text, refs}` objects, up to 20 claims per field, with nonempty text and at least one valid reference per claim. Empty arrays mean unknown or unsupported, including `attention`; they do not establish that everything is fine. Use concise statements rather than copying logs. Distinguish requested goals, recorded actions, verified results, remaining work, decisions, and issues needing attention. Do not equate a tool success, last response, or finished turn with completed user intent.

Save the payload in a private temporary directory (for example, one created by `mktemp -d`) and import it. The payload path contains user data; do not commit it to a repository. The commands for one prepared payload are:

```bash
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" summary-import --input "$dashboard_payload"
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" start
```

Set `dashboard_payload` to the real private JSON file. Import accepts **one session per file**, not the `inputs` envelope or a list. Finish importing the selected sessions before starting or exporting. If no evidence supports any claims, import empty fields and report that limitation. If a selected record cannot produce an input, disclose the error instead of claiming that its summary was created; proceed with unaffected sessions using separate, consistently scoped operations where possible.

Import checks the snapshot/session pair, reference IDs, source continuity, and sequence. A newer accepted summary prevents an older input from overwriting it. On rejected input, issue a fresh snapshot and reassess the claims; never relabel old evidence with new IDs. A valid ordinary append may already yield `stale`; say so and refresh again only if the user's request requires a newer view. Avoid chasing a continuously changing session indefinitely.

`start` returns `{status, reused, url, runtime_dir}`. Open or return the URL exactly as provided, including `/#token=...`; the fragment authenticates the local page and remains available for browser reload. The bearer token is sent only in the API authorization header. Never publish the URL, print it into diagnostic logs, or turn it into an external link preview.

## Refresh, status, and stop

An explicit request to refresh summaries repeats `summary-input` → agent-authored payloads → `summary-import`. The running server observes imports at its next collection. If the user requested a new offline copy, export after imports. Browser “기록 새로고침” and local search/filter actions never run this summary workflow.

```bash
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" status
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" stop
```

`stop` authenticates the registered instance and waits for cleanup. A stale registry PID is not signalled. Use the original selection/options; do not stop an unrelated instance to resolve a conflict. The page retries failed state requests with bounded backoff, pauses after three consecutive failures, and offers “다시 연결”. Authentication failure requires the newly returned dashboard URL.

## Offline export and server failure

```bash
python3 -B "$dashboard_skill/scripts/dashboard.py" "${dashboard_options[@]}" export --output "$PWD/session-dashboard.html"
```

Choose an output path requested by the user or a suitable user-owned artifact directory. For an initial offline dashboard, run the same summary-input/author/import workflow first, then export. For an existing dashboard export, include its existing summaries and disclose stale, invalid, or absent summaries; refresh them if requested.

If a local socket or detached process is unavailable, complete summary generation/import and run this export command with the same options. No server is required for summary operations or export. Return the single HTML file and the actual server error. `file://` supports search, filters, identity, timeline, and captured evidence without any network requests. It is a snapshot: later changes require another export. A missing parser or unreadable source also prevents collection/export; report this distinct blocker honestly rather than claiming an offline fallback succeeded.

## Reading the page

Cards show the human title (or an explicitly automatic title), project path, and full session ID; duplicate names remain distinct. Identity details expose recorded turn state, live-state provenance, observation time, collection time, summary time, and input time. All displayed times use the browser's local timezone.

Summary freshness has three separate meanings:

| State | Meaning |
| --- | --- |
| `fresh` | Source bytes still match the input; this does not establish live execution or the truth of every claim. |
| `stale` | New records were appended; claims remain tied to the captured older evidence. |
| `invalid` | Source continuity failed, such as replacement or rollback; the page suppresses these claims. |

Absent summaries are labelled separately. Only fresh summaries with an attention claim receive priority; other cards follow recent recorded activity. The status filter includes summary states, unknown execution state, and collection warnings. An empty field is explicitly unknown. “근거 보기” resolves references only within `summary.evidence` captured at input time, never the card's current timeline. Collection warnings, truncation counts, and omitted sessions explain the view's limits.


## Claude source boundaries

Stored custom titles take precedence over a registry name, then a stored agent name. Without those, the first retained user request supplies a visibly automatic title, then the short ID is the fallback. Repeated renames, including returning to an earlier title, retain the same full session ID. A saved AI-generated title is not treated as a custom human title.

The adapter reads `sessions/*.json` only during discovery. Changed files are bounded before parsing; unchanged files reuse their cached observation and keep the original read time. Removing a registry entry removes its cached name and reports the time when absence was observed. A registry status such as `busy` or `idle` is only a recorded hint, regardless of its PID. The page always labels live execution as unknown and shows the hint, source modification time, and observation time. Collection time does not refresh the meaning of an old registry record.

The recorded turn state comes from the last conversational record on the active branch. Meta records, compaction summaries, and local-command records such as `/exit` output are skipped. It stays unknown when that record is a user request or tool result without a recorded response.

Transcript bytes, including gzip expansion, are limited to 32 MiB by default before the sibling parser or metadata scan runs. Temporary snapshots are private and erased. Collection defaults to 5 seconds, discovery to 30 seconds, recent events to 40, each text to 2,000 characters, and evidence to 100 events. The view reports omissions, malformed records, and skipped oversized sources. Unchanged transcripts and registry files are not reread.

Evidence includes ancestry-confirmed user messages, assistant text, compaction markers, and minimal tool-result/file-path facts. Reasoning, system instructions, attachment bodies, peer messages, and raw tool input/output are omitted. Sibling parallel tool records may be conservatively omitted; ordinary parallel tool appends do not themselves invalidate a summary. User rewind/edit or replaced plain answers change the conversational lineage, while ordinary append makes an accepted summary stale. A broken parent chain is disclosed. Compaction text bodies are omitted; use the retained requests and responses for claims.

Masking is best effort, not a guarantee that excerpts contain no private information. Keep runtime files and exports private, and inspect the selected evidence before sharing it. The source transcripts and registry remain read-only.
