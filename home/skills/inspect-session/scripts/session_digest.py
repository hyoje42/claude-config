#!/usr/bin/env python3
"""Condense a Claude Code session transcript (JSONL) into what a reader needs.

Subcommands:
  locate   [QUERY]            resolve a session, or list recent sessions
  overview SESSION            one-screen summary of the session
  timeline SESSION [opts]     numbered events: prompts, replies, tool calls
  show     SESSION N [N...]   full content of specific timeline events
  grep     SESSION PATTERN    search all text, including tool inputs/results

SESSION / QUERY accepts a .jsonl path, a session ID or its prefix, a live
session name (optionally with its "[ref]" suffix), or a custom/agent title.

The transcript format is internal to Claude Code and changes between
versions, so unknown record types are skipped instead of failing.
Standard library only.
"""

import argparse
import json
import os
import re
import shlex
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo
except ImportError:  # pragma: no cover
    ZoneInfo = None

CLAUDE_HOME = Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))
PROJECTS = CLAUDE_HOME / "projects"
LIVE_SESSIONS = CLAUDE_HOME / "sessions"

ID_RE = re.compile(r"^[0-9a-f][0-9a-f-]{5,35}$")
TAG_RE = re.compile(r"<([a-z_-]+)>(.*?)</\1>", re.S)
SECRET_RES = [
    re.compile(r"sk-(?:ant-)?[A-Za-z0-9_-]{20,}"),
    re.compile(r"\b(?:ghp|gho|ghs|ghu|github_pat)_[A-Za-z0-9_]{20,}"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{20,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)(\s*[:=]\s*)['\"]?[^\s'\"]{8,}"),
]

CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

KIND_LABEL = {
    "U": "user",
    "P": "peer",
    "/": "cmd",
    "N": "notify",
    "A": "claude",
    "K": "think",
    "T": "tool",
    "C": "compact",
    "S": "recap",
    "F": "file",
}


# ---------------------------------------------------------------- helpers

def redact(text):
    """Mask secrets and strip terminal control characters (keeps tab/newline).

    Session applies this to every event field before clipping or searching, so
    a clip boundary cannot split a secret past its pattern."""
    if not text:
        return text
    text = str(text)
    for rx in SECRET_RES:
        if rx.groups >= 2:
            text = rx.sub(lambda m: m.group(1) + m.group(2) + "[REDACTED]", text)
        else:
            text = rx.sub("[REDACTED]", text)
    return CONTROL_RE.sub("", text)


def redact_deep(value):
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, list):
        return [redact_deep(v) for v in value]
    if isinstance(value, dict):
        return {k: redact_deep(v) for k, v in value.items()}
    return value


def clip(text, width):
    text = (text or "").strip()
    if width and width > 0 and len(text) > width:
        return text[:width].rstrip() + f" …(+{len(text) - width} chars)"
    return text


def one_line(text, width):
    return clip(re.sub(r"\s+", " ", text or ""), width)


def block_text(content):
    """Flatten message/tool-result content into plain text."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for b in content:
            if isinstance(b, dict):
                if b.get("type") == "text":
                    parts.append(b.get("text", ""))
                elif b.get("type") == "image":
                    parts.append("[image]")
                elif b.get("type") == "tool_reference":
                    parts.append(f"[tool {b.get('tool_name', '')}]")
                elif "text" in b:
                    parts.append(str(b["text"]))
            else:
                parts.append(str(b))
        return "\n".join(p for p in parts if p)
    if isinstance(content, dict):
        return block_text([content])
    return str(content)


class Clock:
    def __init__(self, tz_name):
        self.tz = None
        if ZoneInfo and tz_name:
            try:
                self.tz = ZoneInfo(tz_name)
            except Exception:
                self.tz = None
        self.name = tz_name if self.tz else "UTC"

    def parse(self, ts):
        if not ts:
            return None
        try:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None
        return dt.astimezone(self.tz or timezone.utc)

    def fmt(self, ts, full=False):
        dt = self.parse(ts) if isinstance(ts, str) else ts
        if not dt:
            return "--:--" if not full else "?"
        return dt.strftime("%Y-%m-%d %H:%M" if full else "%m-%d %H:%M")


def iter_records(path):
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(rec, dict):
                yield rec


def live_index():
    """sessionId -> live registry entry (only for running sessions)."""
    out = {}
    if not LIVE_SESSIONS.is_dir():
        return out
    for f in LIVE_SESSIONS.glob("*.json"):
        try:
            d = json.loads(f.read_text())
        except Exception:
            continue
        sid = d.get("sessionId")
        pid = d.get("pid")
        if not sid:
            continue
        d["alive"] = bool(pid) and Path(f"/proc/{pid}").exists()
        out[sid] = d
    return out


def quick_meta(path, max_bytes=None):
    """Cheap scan for titles, cwd, last prompt and time span."""
    meta = {"titles": [], "cwd": None, "last_prompt": None, "first_ts": None, "last_ts": None}
    seen = set()
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for i, line in enumerate(fh):
            if not any(k in line for k in ('"custom-title"', '"agent-name"', '"ai-title"',
                                           '"last-prompt"', '"timestamp"')):
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            t = rec.get("type")
            for key in ("customTitle", "agentName", "aiTitle"):
                v = rec.get(key)
                if v and v not in seen:
                    seen.add(v)
                    meta["titles"].append(v)
            if t == "last-prompt" and rec.get("lastPrompt"):
                meta["last_prompt"] = rec["lastPrompt"]
            ts = rec.get("timestamp")
            if ts:
                meta["first_ts"] = meta["first_ts"] or ts
                meta["last_ts"] = ts
            if not meta["cwd"] and rec.get("cwd"):
                meta["cwd"] = rec["cwd"]
    return meta


# ---------------------------------------------------------------- locate

def all_transcripts():
    if not PROJECTS.is_dir():
        return []
    return [p for p in PROJECTS.glob("*/*.jsonl") if p.is_file()]


def resolve(query):
    """Return (path or None, candidates list of (path, reason))."""
    q = (query or "").strip()
    if not q:
        return None, []
    p = Path(os.path.expanduser(q))
    if p.suffix == ".jsonl" and p.is_file():
        return p, []
    name = re.sub(r"\s*\[[^\]]*\]\s*$", "", q).lstrip("@")

    live = live_index()
    hits = []
    # 1) live session name
    for sid, d in live.items():
        if d.get("name") == name:
            hits += [(f, f"live name {name}") for f in PROJECTS.glob(f"*/{sid}.jsonl")]
    if len({h[0] for h in hits}) == 1:
        return hits[0][0], []
    if hits:
        return None, hits
    # 2) session ID or prefix (main sessions, then subagents)
    if ID_RE.match(name.lower()):
        hits = [(f, "session id") for f in PROJECTS.glob(f"*/{name.lower()}*.jsonl")]
        if not hits:
            hits = [(f, "subagent id") for f in PROJECTS.glob(f"*/*/subagents/agent-{name.lower()}*.jsonl")]
        if len(hits) == 1:
            return hits[0][0], []
        if hits:
            return None, hits
    # 3) custom/agent/ai title
    exact, partial = [], []
    needle = name.lower()
    for f in all_transcripts():
        with open(f, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if '"custom-title"' not in line and '"agent-name"' not in line and '"ai-title"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for key in ("customTitle", "agentName", "aiTitle"):
                    v = (rec.get(key) or "").lower()
                    if not v:
                        continue
                    if v == needle:
                        exact.append((f, f"{key} = {rec.get(key)}"))
                    elif needle in v:
                        partial.append((f, f"{key} ~ {rec.get(key)}"))
    for group in (exact, partial):
        uniq = {}
        for f, why in group:
            uniq.setdefault(f, why)
        if len(uniq) == 1:
            return next(iter(uniq)), []
        if uniq:
            return None, list(uniq.items())
    return None, []


def cmd_locate(args, clock):
    live = live_index()
    if args.query:
        path, cands = resolve(args.query)
        if path:
            print(f"RESOLVED {path}")
            return 0
        if not cands:
            print(f"세션을 찾지 못했습니다: {args.query}", file=sys.stderr)
            if not ID_RE.match(args.query.strip().lower()):
                print("종료된 세션은 이름 대신 세션 ID나 경로로 지정해야 할 수 있습니다.", file=sys.stderr)
            return 2
        print(f"AMBIGUOUS: {len(cands)}개 후보가 있습니다. 하나를 골라 ID나 경로로 다시 지정하세요.")
        files = [c[0] for c in cands]
        reasons = dict(cands)
    else:
        files = all_transcripts()
        if args.here:
            slug = re.sub(r"[^A-Za-z0-9]", "-", os.getcwd())
            files = [f for f in files if f.parent.name == slug]
        reasons = {}
    files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)[: args.limit]
    for f in files:
        sid = f.stem
        m = quick_meta(f)
        d = live.get(sid)
        state = ""
        if d and d.get("alive"):
            state = f"LIVE {d.get('name')} ({d.get('status')})"
        if args.self_id and sid == args.self_id:
            state = (state + " " if state else "") + "[this session]"
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc)
        print(f"- {sid}  {clock.fmt(mtime.astimezone(clock.tz or timezone.utc), full=True)}  {f.stat().st_size // 1024}KB  {state}".rstrip())
        print(f"    cwd: {m['cwd'] or '?'}")
        if m["titles"]:
            print(f"    title: {' / '.join(m['titles'][-3:])}")
        if m["last_prompt"]:
            print(f"    last prompt: {one_line(redact(m['last_prompt']), 120)}")
        if f in reasons:
            print(f"    matched: {reasons[f]}")
        print(f"    path: {f}")
    return 0


# ---------------------------------------------------------------- parsing

def tool_summary(name, inp, width):
    inp = inp if isinstance(inp, dict) else {}
    g = inp.get
    if name == "Bash":
        desc = g("description") or ""
        cmd = one_line(g("command", ""), 100)
        s = f"{desc} $ {cmd}" if desc else f"$ {cmd}"
        if g("run_in_background"):
            s += " [bg]"
        return s
    if name in ("Read", "Write", "Edit", "MultiEdit", "NotebookEdit"):
        path = g("file_path") or g("notebook_path") or ""
        extra = ""
        if name == "Write":
            extra = f" ({len((g('content') or '').splitlines())} lines)"
        elif name == "Read" and (g("offset") or g("limit")):
            extra = " (" + ", ".join(f"{k}={g(k)}" for k in ("offset", "limit") if g(k)) + ")"
        elif name == "Edit" and g("replace_all"):
            extra = " (replace_all)"
        return path + extra
    if name in ("Grep", "Glob"):
        return f"{g('pattern', '')}  in {g('path') or '.'}"
    if name in ("Agent", "Task"):
        bits = [g("subagent_type") or "", g("description") or ""]
        if g("run_in_background"):
            bits.append("[bg]")
        return " ".join(b for b in bits if b)
    if name == "SendMessage":
        return f"to={g('to')} : {one_line(str(g('message', '')), 120)}"
    if name == "Skill":
        return f"{g('skill')} {g('args') or ''}".strip()
    if name == "WebFetch":
        return g("url", "")
    if name == "WebSearch":
        return g("query", "")
    if name == "AskUserQuestion":
        qs = g("questions") or []
        return " | ".join(one_line(q.get("question", ""), 100) for q in qs if isinstance(q, dict))
    if name == "TodoWrite":
        todos = g("todos") or []
        return f"{len(todos)} todos"
    return one_line(json.dumps(inp, ensure_ascii=False), width or 140)


ALWAYS_SHOW_RESULT = {"AskUserQuestion", "ExitPlanMode"}
FILE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
# Words that may precede a command in the same simple command.
SHELL_KEYWORDS = {"if", "then", "elif", "else", "while", "until", "do", "!", "{", "time"}
COMMAND_PREFIXES = {"sudo", "env", "command", "exec", "nohup", "time"}
SHELLS = {"bash", "sh", "zsh"}
GIT_OPTIONS_WITH_ARG = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def state_command(words):
    """Recognize command positions, never command names inside arguments."""
    words = [word[1:-1] if len(word) > 1 and word[0] == word[-1] and word[0] in "'\""
             else word for word in words]
    while words:
        head = words[0]
        if re.match(r"^[A-Za-z_]\w*=", head) or head in SHELL_KEYWORDS:
            words = words[1:]
        elif head in COMMAND_PREFIXES:
            words = words[1:]
            # Prefix options such as `sudo -E` or `env -i`; `sudo -u USER` takes a value.
            while words and words[0].startswith("-"):
                words = words[2:] if words[0] in ("-u", "-g") else words[1:]
        elif Path(head).name in SHELLS and len(words) > 1 and not words[1].startswith("-"):
            words = words[1:]
        else:
            break
    if not words:
        return False
    name = Path(words[0]).name
    if name.endswith("sync-to-home"):
        return not any(flag in words[1:] for flag in ("--dry-run", "-n"))
    if name != "git":
        return False
    args = words[1:]
    while args and args[0].startswith("-"):
        args = args[2:] if args[0] in GIT_OPTIONS_WITH_ARG else args[1:]
    if not args:
        return False
    subcommand, rest = args[0], args[1:]
    if subcommand in {"commit", "push", "pull", "reset", "rebase", "merge", "cherry-pick",
                      "revert", "checkout", "switch", "restore", "clean", "rm", "mv"}:
        return True
    if subcommand == "stash":
        return not rest or rest[0] not in {"list", "show"}
    if subcommand == "tag":
        return bool(rest) and (not rest[0].startswith("-") or
                              rest[0] in {"-a", "-s", "-d", "-f", "--delete", "--force"})
    if subcommand == "submodule":
        return bool(rest) and rest[0] == "update"
    return subcommand == "branch" and bool(rest) and rest[0] in {"-d", "-D", "-m", "-M"}


def state_shell_call(command):
    """Conservative shell scan; retain the call's control flow, omit heredoc bodies.

    This is not a shell interpreter. Matches are candidates, never proof that
    a branch ran. Unsupported or unfinished quoting is not guessed.
    """
    headers, heredocs = [], []
    pending = ""
    found = False
    for line in command.splitlines():
        if heredocs:
            delimiter, strip_tabs = heredocs[0]
            if (line.lstrip("\t") if strip_tabs else line) == delimiter:
                heredocs.pop(0)
            continue
        pending += line
        if pending.endswith("\\"):
            pending = pending[:-1]
            continue
        lexer = shlex.shlex(pending, posix=False, punctuation_chars=";&|()<>")
        lexer.whitespace_split = True
        # shlex would start a comment at any `#`, even inside a word such as a URL
        # fragment; the shell does so only at the start of a word.
        lexer.commenters = ""
        try:
            tokens = list(lexer)
        except ValueError:
            pending += "\n"
            continue
        comment = next((i for i, token in enumerate(tokens) if token.startswith("#")), None)
        if comment is not None:
            tokens = tokens[:comment]
        headers.append(pending)
        pending = ""
        for index, token in enumerate(tokens[:-1]):
            if token == "<<":
                delimiter = tokens[index + 1]
                strip_tabs = delimiter.startswith("-")
                delimiter = delimiter[1:] if strip_tabs else delimiter
                if len(delimiter) > 1 and delimiter[0] == delimiter[-1] and delimiter[0] in "'\"":
                    delimiter = delimiter[1:-1]
                heredocs.append((delimiter, strip_tabs))
        words = []
        for token in tokens + [";"]:
            if token and all(char in ";&|()" for char in token):
                found = state_command(words) or found
                words = []
            else:
                words.append(token)
    if pending or heredocs:
        return ""
    return "\n".join(headers) if found else ""


HANDBACK_FRAME = re.compile(r"\[Subagent hand-back\][^\n]*?The report follows:[ \t]*\n?")


def parse_tags(text):
    return {m.group(1): m.group(2).strip() for m in TAG_RE.finditer(text)}


class Session:
    def __init__(self, path, include_thinking=False):
        self.path = Path(path)
        self.events = []
        self.records_by_uuid = {}
        self.results = {}
        self.meta = {"titles": [], "cwds": Counter(), "branches": Counter(), "versions": Counter(),
                     "first_ts": None, "last_ts": None, "last_prompt": None, "types": Counter()}
        self.include_thinking = include_thinking
        self._peer_seen = set()
        self.rewound = 0
        self._parse()

    def _add(self, kind, rec, text, **extra):
        ev = {"n": len(self.events) + 1, "kind": kind, "ts": rec.get("timestamp"),
              "uuid": rec.get("uuid"), "text": redact(text), "off": False}
        ev.update(redact_deep(extra))
        self.events.append(ev)
        return ev

    def _parse(self):
        meta = self.meta
        tool_events = {}
        seen_titles = set()
        last_uuid = None
        for rec in iter_records(self.path):
            t = rec.get("type")
            meta["types"][t] += 1
            for key in ("customTitle", "agentName", "aiTitle"):
                v = rec.get(key)
                if v and v not in seen_titles:
                    seen_titles.add(v)
                    meta["titles"].append(v)
            if t == "last-prompt":
                meta["last_prompt"] = rec.get("lastPrompt")
            ts = rec.get("timestamp")
            if ts:
                meta["first_ts"] = meta["first_ts"] or ts
                meta["last_ts"] = ts
            if rec.get("uuid"):
                self.records_by_uuid[rec["uuid"]] = rec
                if t in ("user", "assistant", "system"):
                    last_uuid = rec["uuid"]
            if t in ("user", "assistant"):
                if rec.get("cwd"):
                    meta["cwds"][rec["cwd"]] += 1
                if rec.get("gitBranch"):
                    meta["branches"][rec["gitBranch"]] += 1
                if rec.get("version"):
                    meta["versions"][rec["version"]] += 1

            try:
                if t == "user":
                    self._user(rec, tool_events)
                elif t == "assistant":
                    self._assistant(rec, tool_events)
                elif t == "system":
                    self._system(rec)
                elif t == "attachment":
                    self._attachment(rec)
            except Exception as exc:  # keep going on format drift
                self._add("N", rec, f"[parse error on {t}: {exc}]")
        self.leaf = last_uuid
        self._mark_rewinds()

    # -- record handlers
    def _user(self, rec, tool_events):
        msg = rec.get("message") or {}
        content = msg.get("content")
        if rec.get("isCompactSummary"):
            self._add("C", rec, block_text(content))
            return
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            for b in content:
                if not (isinstance(b, dict) and b.get("type") == "tool_result"):
                    continue
                tid = b.get("tool_use_id")
                res = {"error": bool(b.get("is_error")), "text": redact(block_text(b.get("content")))}
                tur = rec.get("toolUseResult")
                if isinstance(tur, dict) and tur.get("interrupted"):
                    res["interrupted"] = True
                if isinstance(tur, dict) and tur.get("backgroundTaskId"):
                    res["background"] = True
                self.results[tid] = res
                ev = tool_events.get(tid)
                if ev is not None:
                    ev["result"] = res
            return
        text = block_text(content)
        origin = rec.get("origin") or {}
        okind = origin.get("kind") if isinstance(origin, dict) else None
        if okind == "peer" or text.startswith("Another Claude session sent a message"):
            self._peer(rec, origin if isinstance(origin, dict) else {}, text)
            return
        if rec.get("isMeta"):
            return
        stripped = text.lstrip()
        if okind == "task-notification" or stripped.startswith("<task-notification"):
            tags = parse_tags(text)
            summary = tags.get("summary") or one_line(text, 200)
            status = tags.get("status")
            self._add("N", rec, summary, status=status, raw=text)
            return
        if stripped.startswith("<command-name>") or stripped.startswith("<command-message>"):
            tags = parse_tags(text)
            name = tags.get("command-name") or "/" + tags.get("command-message", "?")
            args = tags.get("command-args", "")
            self._add("/", rec, f"{name} {args}".strip(), pending_stdout=True)
            return
        if stripped.startswith("<local-command-stdout>") or stripped.startswith("<local-command-stderr>"):
            tags = parse_tags(text)
            out = tags.get("local-command-stdout") or tags.get("local-command-stderr") or ""
            for ev in reversed(self.events[-3:]):
                if ev["kind"] == "/" and ev.get("pending_stdout"):
                    ev["stdout"] = redact(out)
                    ev["pending_stdout"] = False
                    break
            return
        if stripped.startswith("<bash-input>"):
            tags = parse_tags(text)
            self._add("/", rec, "! " + tags.get("bash-input", ""))
            return
        if stripped.startswith("<bash-stdout>") or stripped.startswith("<bash-stderr>"):
            return
        self._add("U", rec, text, from_record=True)

    def _peer(self, rec, origin, text, queued=False):
        """Peer messages can be logged twice (queued attachment + user record)."""
        m = re.search(r'from-name="([^"]*)"', text)
        sender = origin.get("name") or (m.group(1) if m else None) or origin.get("from")
        body = origin.get("body")
        if not body:
            body = re.sub(r"^Another Claude session sent a message:\s*", "", text)
            body = re.sub(r"</?cross-session-message[^>]*>", "", body).strip()
        key = origin.get("msg_id") or (sender, body[:200])
        if key in self._peer_seen:
            return
        self._peer_seen.add(key)
        extra = {"queued": True} if queued else {}
        # The harness wraps subagent reports in a fixed frame and indents the report;
        # drop the frame so previews start with the report itself.
        m = HANDBACK_FRAME.match(body)
        if m:
            body = re.sub(r"(?m)^  ", "", body[m.end():]).strip()
            extra["handback"] = True
        self._add("P", rec, body, sender=sender, **extra)

    def _assistant(self, rec, tool_events):
        msg = rec.get("message") or {}
        content = msg.get("content")
        if isinstance(content, str):
            content = [{"type": "text", "text": content}]
        for b in content or []:
            if not isinstance(b, dict):
                continue
            bt = b.get("type")
            if bt == "text" and b.get("text", "").strip():
                self._add("A", rec, b["text"])
            elif bt == "thinking" and self.include_thinking and (b.get("thinking") or "").strip():
                self._add("K", rec, b["thinking"])
            elif bt == "tool_use":
                name = b.get("name", "?")
                ev = self._add("T", rec, "", tool=name, input=b.get("input"), tool_id=b.get("id"))
                tool_events[b.get("id")] = ev
                if b.get("id") in self.results:
                    ev["result"] = self.results[b.get("id")]

    def _system(self, rec):
        st = rec.get("subtype")
        if st == "away_summary":
            text = re.sub(r"\s*\(disable recaps in /config\)\s*$", "", rec.get("content") or "")
            self._add("S", rec, text)
        elif st == "compact_boundary":
            cm = rec.get("compactMetadata") or {}
            self._add("C", rec, f"--- compacted ({cm.get('trigger', '?')}, {cm.get('preTokens', '?')} tokens before) ---",
                      boundary=True)
        elif st == "local_command":
            pass

    def _attachment(self, rec):
        a = rec.get("attachment") or {}
        at = a.get("type")
        if at == "queued_command" and a.get("commandMode") == "prompt":
            origin = a.get("origin")
            if isinstance(origin, str):
                try:
                    origin = json.loads(origin)
                except json.JSONDecodeError:
                    origin = {}
            okind = (origin or {}).get("kind")
            prompt = block_text(a.get("prompt"))
            if okind == "peer":
                self._peer(rec, origin or {}, prompt, queued=True)
            elif okind == "human" or a.get("humanTurn"):
                self._add("U", rec, prompt, queued=True)
        elif at == "edited_text_file" and a.get("filename"):
            self._add("F", rec, f"file changed outside this session: {a['filename']}")
        elif at == "file" and a.get("filename"):
            self._add("F", rec, f"@-attached: {a['filename']}")

    def _mark_rewinds(self):
        """Mark events on branches abandoned by rewind/edit.

        Parallel tool calls also fork parentUuid, so only human prompts decide
        whether a segment is on the final branch."""
        if not self.leaf:
            return
        anc, cur, guard = set(), self.leaf, 0
        while cur and cur not in anc and guard < 1_000_000:
            anc.add(cur)
            rec = self.records_by_uuid.get(cur) or {}
            cur = rec.get("parentUuid") or rec.get("logicalParentUuid")
            guard += 1
        if len(anc) < 2:
            return
        off = False
        for ev in self.events:
            if ev["kind"] == "U" and ev.get("from_record"):
                off = ev["uuid"] not in anc
            ev["off"] = off
        self.rewound = sum(1 for e in self.events if e["kind"] == "U" and e["off"])

    # -- derived
    def compactions(self):
        return [e for e in self.events if e["kind"] == "C" and e.get("boundary")]

    def state_ops(self):
        """Bash calls containing candidate state operations, with call-level results."""
        ops = []
        for e in self.events:
            if e["kind"] != "T" or e.get("tool") != "Bash":
                continue
            cmd = (e.get("input") or {}).get("command") or ""
            command = state_shell_call(cmd)
            if command:
                ops.append((e, command))
        return ops

    def changed_files(self):
        c = Counter()
        for e in self.events:
            if e["kind"] == "T" and e.get("tool") in FILE_TOOLS and not (e.get("result") or {}).get("error"):
                inp = e.get("input") or {}
                p = inp.get("file_path") or inp.get("notebook_path")
                if p:
                    c[p] += 1
        return c


# ---------------------------------------------------------------- render

def fmt_event(ev, clock, width, tool_width, show_results):
    k = ev["kind"]
    head = f"#{ev['n']:<4} {clock.fmt(ev['ts'])} {KIND_LABEL.get(k, k):<8}"
    if ev.get("off"):
        head += "[rewound] "
    if k == "T":
        name = ev.get("tool")
        line = f"{head}{name}: {tool_summary(name, ev.get('input'), tool_width)}"
        res = ev.get("result")
        if res is None:
            line += "  (no result)"
        elif res.get("interrupted"):
            line += "  → INTERRUPTED"
        elif res.get("error"):
            line += f"  → ERROR: {one_line(res.get('text'), 200)}"
        elif name in ALWAYS_SHOW_RESULT or show_results:
            line += f"\n        → {clip(res.get('text'), max(width, 300)).replace(chr(10), chr(10) + '          ')}"
        return redact(line)
    if k == "/":
        line = f"{head}{ev['text']}"
        if ev.get("stdout"):
            line += f"  → {one_line(ev['stdout'], 160)}"
        return redact(line)
    if k == "N":
        st = f"[{ev['status']}] " if ev.get("status") else ""
        return redact(f"{head}{st}{one_line(ev['text'], 240)}")
    if k == "F":
        return redact(f"{head}{ev['text']}")
    label = ""
    if k == "P":
        label = f"from {ev.get('sender') or '?'}{' (subagent report)' if ev.get('handback') else ''}: "
    if ev.get("queued"):
        label = "(sent mid-turn) " + label
    w = width
    if k in ("U", "P", "S"):
        w = max(width * 2, 1200)
    if k == "C" and not ev.get("boundary"):
        w = max(width * 4, 6000)
    body = clip(ev["text"], w).replace("\n", "\n        ")
    return redact(f"{head}{label}{body}")


def load(args):
    path, cands = resolve(args.session)
    if not path:
        if cands:
            print("세션 후보가 여러 개입니다. ID나 경로로 다시 지정하세요:", file=sys.stderr)
            for f, why in cands:
                print(f"  {f}  ({why})", file=sys.stderr)
        else:
            print(f"세션을 찾지 못했습니다: {args.session}", file=sys.stderr)
        sys.exit(2)
    return Session(path, include_thinking=getattr(args, "thinking", False))


def cmd_overview(args, clock):
    s = load(args)
    m = s.meta
    sid = s.path.stem
    live = live_index().get(sid)
    ev = s.events
    kinds = Counter(e["kind"] for e in ev)
    tools = Counter(e["tool"] for e in ev if e["kind"] == "T")
    errors = [e for e in ev if e["kind"] == "T" and (e.get("result") or {}).get("error")]
    humans = [e for e in ev if e["kind"] == "U" and not e.get("off")]
    claude = [e for e in ev if e["kind"] == "A" and not e.get("off")]
    recaps = [e for e in ev if e["kind"] == "S"]
    peers = Counter(e.get("sender") or "?" for e in ev if e["kind"] == "P")

    def top(counter, n):
        return ", ".join(f"{k} {v}" for k, v in counter.most_common(n)) or "none"

    print(f"session   {sid}")
    print(f"file      {s.path} ({s.path.stat().st_size // 1024}KB)")
    if live and live.get("alive"):
        print(f"live      name={live.get('name')} status={live.get('status')} pid={live.get('pid')}"
              + ("  ← still recording; content may change" if live.get("status") == "busy" else ""))
    else:
        print("live      not running")
    if args.self_id and sid == args.self_id:
        print("note      this is the current session")
    print(f"title     {' / '.join(m['titles']) or 'none'}")
    print(f"cwd       {top(m['cwds'], 3)}")
    print(f"branch    {top(m['branches'], 3)}")
    print(f"version   {top(m['versions'], 2)}")
    print(f"time      {clock.fmt(m['first_ts'], True)} → {clock.fmt(m['last_ts'], True)} ({clock.name})")
    print(f"counts    user prompts {kinds['U']}, claude replies {kinds['A']}, tool calls {kinds['T']}, "
          f"tool errors {len(errors)}, peer msgs {kinds['P']}, notifications {kinds['N']}, "
          f"compactions {len(s.compactions())}, rewound prompts {s.rewound}")
    print(f"tools     {top(tools, 10)}")
    if peers:
        print(f"peers     {top(peers, 6)}")
    files = s.changed_files()
    if files:
        print("changed   (Write/Edit only; Bash-made changes are not tracked)")
        for p, c in files.most_common(args.files):
            print(f"          {p} ×{c}")
        if len(files) > args.files:
            print(f"          … +{len(files) - args.files} more")
    ops = s.state_ops()
    if ops:
        print("git·sync 명령 후보를 포함한 셸 호출 (전체 호출 결과; 개별 실행 여부는 미확인):")
        for e, line in ops[-args.ops:]:
            res = e.get("result")
            if res is None:
                st = "결과 없음"
            elif res.get("interrupted"):
                st = "중단됨"
            elif res.get("background"):
                st = "백그라운드 실행"
            else:
                st = "호출 실패" if res.get("error") else "호출 정상 반환"
            mark = " [rewound]" if e.get("off") else ""
            print(f"          #{e['n']} {clock.fmt(e['ts'])} {st}{mark}  {redact(one_line(line, 140))}")
        if len(ops) > args.ops:
            print(f"          … 이전 호출 {len(ops) - args.ops}개 생략")
    sub = s.path.parent / sid / "subagents"
    if sub.is_dir():
        metas = sorted(sub.glob("agent-*.meta.json"))
        print(f"subagents {len(list(sub.glob('agent-*.jsonl')))} transcript(s) in {sub}")
        for mf in metas[: args.files]:
            try:
                d = json.loads(mf.read_text())
            except Exception:
                d = {}
            aid = mf.name.replace("agent-", "").replace(".meta.json", "")
            print(f"          {aid}  {d.get('agentType', '?')}: {one_line(d.get('description', ''), 80)}")
    tr = s.path.parent / sid / "tool-results"
    if tr.is_dir():
        print(f"spilled   large tool outputs saved in {tr}")
    w = args.width
    if humans:
        print(f"\nfirst request  #{humans[0]['n']} {clock.fmt(humans[0]['ts'])}\n  {redact(clip(humans[0]['text'], w * 2))}")
        if len(humans) > 1:
            print(f"\nlast request   #{humans[-1]['n']} {clock.fmt(humans[-1]['ts'])}\n  {redact(clip(humans[-1]['text'], w * 2))}")
    elif m["last_prompt"]:
        print(f"\nlast request\n  {redact(clip(m['last_prompt'], w * 2))}")
    if recaps:
        print(f"\nlatest recap   #{recaps[-1]['n']} {clock.fmt(recaps[-1]['ts'])}\n  {redact(recaps[-1]['text'])}")
    if claude:
        print(f"\nlast reply     #{claude[-1]['n']} {clock.fmt(claude[-1]['ts'])}\n  "
              + redact(clip(claude[-1]['text'], w * 2)).replace("\n", "\n  "))
    if errors:
        print(f"\nrecent tool errors: " + ", ".join(f"#{e['n']} {e['tool']}" for e in errors[-5:]))
    return 0


def cmd_timeline(args, clock):
    s = load(args)
    ev = s.events
    kinds = set(args.kinds.upper().replace("CMD", "/").split(",")) if args.kinds else None
    if kinds:
        kinds = {k.strip() for k in kinds if k.strip()}
    start = 1
    comp = s.compactions()
    note = None
    if not args.full and comp and args.from_n is None and args.last is None:
        start = comp[-1]["n"]
        note = f"(showing from the last compaction #{start}; earlier: --full or --from N)"
    if args.from_n is not None:
        start = args.from_n
    sel = [e for e in ev if e["n"] >= start and (args.to_n is None or e["n"] <= args.to_n)]
    if kinds:
        sel = [e for e in sel if e["kind"] in kinds or (e["kind"] == "C")]
    if args.no_rewound:
        sel = [e for e in sel if not e.get("off")]
    if args.last:
        sel = sel[-args.last:]
    print(f"# {s.path.stem}  events {len(ev)}  showing {len(sel)}  times {clock.name}")
    print("# kinds: user, claude, tool, peer, cmd, notify, recap, compact, file" + (", think" if args.thinking else ""))
    if note:
        print("# " + note)
    for e in sel:
        print(fmt_event(e, clock, args.width, args.width, args.results))
    return 0


def cmd_show(args, clock):
    s = load(args)
    by_n = {e["n"]: e for e in s.events}
    wanted = []
    for spec in args.n:
        if "-" in spec:
            a, b = spec.split("-", 1)
            wanted += list(range(int(a), int(b) + 1))
        else:
            wanted.append(int(spec))
    for n in wanted:
        e = by_n.get(n)
        if not e:
            print(f"#{n}: no such event")
            continue
        print(f"===== #{n} {KIND_LABEL.get(e['kind'], e['kind'])} {clock.fmt(e['ts'], True)}"
              + (" [rewound]" if e.get("off") else ""))
        if e["kind"] == "T":
            print(f"tool: {e.get('tool')}")
            print("input:")
            print(redact(clip(json.dumps(e.get("input"), ensure_ascii=False, indent=2), args.max)))
            res = e.get("result")
            if res is None:
                print("result: (none recorded)")
            else:
                flag = " [ERROR]" if res.get("error") else ""
                print(f"result{flag}:")
                print(redact(clip(res.get("text"), args.max)))
        elif e["kind"] == "N":
            print(redact(clip(e.get("raw") or e["text"], args.max)))
        else:
            if e.get("sender"):
                print(f"from: {e['sender']}")
            if e.get("stdout"):
                print(redact(clip(e["text"] + "\n→ " + e["stdout"], args.max)))
            else:
                print(redact(clip(e["text"], args.max)))
    return 0


def cmd_grep(args, clock):
    s = load(args)
    rx = re.compile(args.pattern, re.I if args.ignore_case else 0)
    hits = 0
    for e in s.events:
        fields = [("text", e.get("text") or "")]
        if e["kind"] == "T":
            fields.append(("input", json.dumps(e.get("input"), ensure_ascii=False)))
            fields.append(("result", (e.get("result") or {}).get("text") or ""))
        for label, val in fields:
            m = rx.search(val)
            if not m:
                continue
            a, b = max(0, m.start() - 80), min(len(val), m.end() + 80)
            snippet = one_line(val[a:b], 0)
            tool = f" {e.get('tool')}" if e["kind"] == "T" else ""
            print(redact(f"#{e['n']:<4} {clock.fmt(e['ts'])} {KIND_LABEL.get(e['kind'])}{tool} [{label}] …{snippet}…"))
            hits += 1
            break
        if hits >= args.max_hits:
            print(f"(stopped at {args.max_hits} hits; use --max-hits)")
            break
    if not hits:
        print("no match")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tz", default=os.environ.get("INSPECT_SESSION_TZ", "Asia/Seoul"))
    ap.add_argument("--self", dest="self_id", default=None, help="current session ID, to flag it")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("locate", help="resolve a session or list recent ones")
    p.add_argument("query", nargs="?")
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--here", action="store_true", help="only sessions whose project dir matches the cwd")

    p = sub.add_parser("overview", help="one-screen summary")
    p.add_argument("session")
    p.add_argument("--width", type=int, default=500)
    p.add_argument("--files", type=int, default=15)
    p.add_argument("--ops", type=int, default=15, help="max git/sync shell calls to list")

    p = sub.add_parser("timeline", help="numbered event list")
    p.add_argument("session")
    p.add_argument("--full", action="store_true", help="start from the beginning even if compacted")
    p.add_argument("--from", dest="from_n", type=int)
    p.add_argument("--to", dest="to_n", type=int)
    p.add_argument("--last", type=int, help="only the last N selected events")
    p.add_argument("--kinds", help="comma list of U,A,T,P,/,N,S,C,F,K (e.g. U,A,P,S for conversation only)")
    p.add_argument("--width", type=int, default=600, help="max chars per claude reply")
    p.add_argument("--results", action="store_true", help="also print successful tool results")
    p.add_argument("--thinking", action="store_true", help="include non-empty thinking blocks")
    p.add_argument("--no-rewound", action="store_true", help="hide branches abandoned by rewind")

    p = sub.add_parser("show", help="full content of events")
    p.add_argument("session")
    p.add_argument("n", nargs="+", help="event numbers or ranges like 40-45")
    p.add_argument("--max", type=int, default=8000)
    p.add_argument("--thinking", action="store_true")

    p = sub.add_parser("grep", help="search text, tool inputs and results")
    p.add_argument("session")
    p.add_argument("pattern")
    p.add_argument("-i", "--ignore-case", action="store_true")
    p.add_argument("--max-hits", type=int, default=40)
    p.add_argument("--thinking", action="store_true")

    args = ap.parse_args(argv)
    if args.self_id and "${" in args.self_id:
        args.self_id = None
    clock = Clock(args.tz)
    handler = {"locate": cmd_locate, "overview": cmd_overview, "timeline": cmd_timeline,
               "show": cmd_show, "grep": cmd_grep}[args.cmd]
    try:
        rc = handler(args, clock)
        sys.stdout.flush()
        return rc
    except BrokenPipeError:
        # Reader (e.g. `head`) closed the pipe; silence the shutdown flush error.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 0


if __name__ == "__main__":
    sys.exit(main())
