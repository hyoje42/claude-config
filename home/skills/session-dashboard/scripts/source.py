"""Claude adapter: bounded snapshots reuse the sibling inspect-session parser."""

import hashlib
import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

sys.dont_write_bytecode = True
TOOL = "claude"
ADAPTER_VERSION = 1


class SourceError(Exception):
    def __init__(self, message, observation=None):
        super().__init__(message)
        # Private, bounded hash proof; never contains source bytes or excerpts.
        self.observation = observation


def byte_proof(data, checkpoints=()):
    sizes = {size for size in checkpoints if 0 <= size <= len(data)} | {len(data)}
    hasher, prefixes, start = hashlib.sha256(), {}, 0
    view = memoryview(data)
    for size in sorted(sizes):
        hasher.update(view[start:size])
        prefixes[str(size)] = hasher.hexdigest()
        start = size
    return {"size": len(data), "digest": hasher.hexdigest(), "prefixes": prefixes}


def expand_gzip(physical, limit):
    """Bound the decoder itself, including concatenated members and padding."""
    pending, expanded = physical, bytearray()
    while pending:
        decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        expanded.extend(decoder.decompress(pending, limit + 1 - len(expanded)))
        if len(expanded) > limit:
            return bytes(expanded)
        if not decoder.eof:
            raise EOFError("incomplete gzip member")
        pending = decoder.unused_data.lstrip(b"\x00")
    return bytes(expanded)


def dependency(path=None):
    path = path or Path(__file__).resolve().parents[2] / "inspect-session/scripts/session_digest.py"
    try:
        spec = importlib.util.spec_from_file_location("dashboard_session_digest", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name in ("Session", "redact", "iter_records"):
            if not callable(getattr(module, name, None)):
                raise AttributeError(name)
        return module
    except (OSError, ImportError, AttributeError, TypeError, SyntaxError) as exc:
        raise SourceError("inspect-session 의존성이 없거나 호환되지 않습니다. 같은 skills 폴더에 inspect-session을 설치하세요.") from exc


def defaults():
    # CLAUDE_SESSION_ID is a skill substitution, not a shell environment contract.
    return {"home": str(Path(os.environ.get("CLAUDE_CONFIG_DIR", Path.home() / ".claude"))),
            "self_id": None}


def signature(path):
    info = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode):
        raise SourceError("일반 파일이 아닌 기록은 읽지 않습니다.")
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def observed_now():
    return datetime.now(timezone.utc).isoformat()


class Adapter:
    tool = TOOL
    version = ADAPTER_VERSION

    def __init__(self, home, max_bytes, text_limit=2000, recent_limit=40, evidence_limit=100,
                 parser_path=None):
        self.parser = dependency(parser_path)
        self.home = Path(home)
        # Only Session(snapshot) is called. Bind globals too, so no parser helper
        # can accidentally fall back to the operator's real tool home.
        self.parser.CLAUDE_HOME = self.home
        self.parser.PROJECTS = self.home / "projects"
        self.parser.LIVE_SESSIONS = self.home / "sessions"
        self.max_bytes = max_bytes
        self.text_limit = text_limit
        self.recent_limit = recent_limit
        self.evidence_limit = evidence_limit
        self.titles = {}
        self.transcript_titles = {}
        self.registry_cache = {}
        self.registry = {}
        self.registry_observed_at = None
        self.registry_available = True
        self.metrics = {"read_calls": 0, "read_bytes": 0, "expanded_bytes": 0,
                        "parse_calls": 0, "metadata_reads": 0, "registry_reads": 0}

    def clean(self, value, limit=None):
        text = self.parser.redact(str(value or ""))
        text = re.sub(r"(?is)<(attachment|attached_files|file_content|file|environment_context|"
                      r"instructions|system-reminder|permissions|skill|command-message)(?:\s[^>]*)?>.*?</\1\s*>",
                      "[첨부·주입 본문 제외]", text)
        return text[:self.text_limit if limit is None else limit]

    def bounded(self, path, limit=None, checkpoints=()):
        """Read physical bytes once; independently bound raw and expanded snapshots."""
        limit = self.max_bytes if limit is None else limit
        observed_ns = time.time_ns()
        before = signature(path)
        if before[2] > limit:
            raise SourceError("기록 파일이 바이트 상한을 초과하여 수집하지 않았습니다.")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        with os.fdopen(fd, "rb") as raw:
            info = os.fstat(raw.fileno())
            if (info.st_dev, info.st_ino) != before[:2]:
                raise SourceError("읽기 전에 기록 파일이 교체되었습니다.")
            self.metrics["read_calls"] += 1
            physical = raw.read(limit + 1)
            self.metrics["read_bytes"] += len(physical)
        if signature(path) != before:
            raise SourceError("읽는 동안 기록이 바뀌었습니다. 다음 수집에서 다시 확인합니다.")
        if len(physical) > limit:
            raise SourceError("기록 파일이 바이트 상한을 초과하여 수집하지 않았습니다.")
        observation = {"observed_ns": observed_ns, "file_stat": list(before),
                       "raw": byte_proof(physical, checkpoints), "logical": None, "failure": None}
        if path.suffix == ".gz":
            try:
                data = expand_gzip(physical, limit)
            except (OSError, EOFError, zlib.error) as exc:
                observation["failure"] = "decode"
                raise SourceError("압축 기록이 손상되어 해제할 수 없습니다.", observation) from exc
        else:
            data = physical
        self.metrics["expanded_bytes"] += len(data)
        if len(data) > limit:
            observation["failure"] = "bounds"
            raise SourceError("압축 해제된 기록이 바이트 상한을 초과하여 수집하지 않았습니다.", observation)
        observation["logical"] = byte_proof(data, checkpoints)
        return data, before, observation


    def _title(self, sid):
        stored = self.transcript_titles.get(sid, {})
        value = stored.get("customTitle") or self.registry.get(sid, {}).get("name") or stored.get("agentName")
        if value:
            self.titles[sid] = value
        else:
            self.titles.pop(sid, None)

    def discover(self):
        warnings = []
        self.registry_observed_at = observed_now()
        self.registry_available = True
        try:
            directory = self.home / "sessions"
            registry_paths = list(directory.glob("*.json")) if directory.exists() else []
        except OSError:
            registry_paths = []
            self.registry_available = False
            warnings.append("세션 레지스트리 목록을 읽을 수 없습니다. 실행 여부는 확인되지 않았습니다.")
        entries = {}
        retained = {}
        for path in registry_paths:
            current = None
            try:
                current = signature(path)
                cached = self.registry_cache.get(path)
                if cached and cached[0] == current:
                    entry, warning = cached[1:]
                else:
                    data, current, _ = self.bounded(path, min(self.max_bytes, 1024 * 1024))
                    self.metrics["registry_reads"] += 1
                    raw = json.loads(data)
                    if not isinstance(raw, dict) or not isinstance(raw.get("sessionId"), str) or not raw["sessionId"].strip():
                        raise ValueError("invalid registry identity")
                    entry = {"id": self.clean(raw["sessionId"], 200),
                             "name": self.clean(raw.get("name"), 240),
                             "status": self.clean(raw.get("status"), 100),
                             "observed_at": observed_now(), "mtime": current[3]}
                    warning = None
            except (OSError, SourceError, ValueError, TypeError):
                entry, warning = None, "세션 레지스트리 항목을 읽거나 해석할 수 없습니다. 실행 여부는 확인되지 않았습니다."
            retained[path] = (current, entry, warning)
            if warning:
                self.registry_available = False
                warnings.append(warning)
            if entry and (entry["id"] not in entries or entry["mtime"] > entries[entry["id"]]["mtime"]):
                entries[entry["id"]] = entry
        self.registry_cache, self.registry = retained, entries
        for sid in set(self.titles) | set(self.transcript_titles) | set(entries):
            self._title(sid)
        # Main records are exactly one project directory below projects/. Never
        # infer a cwd from the escaped directory name or descend into subagents/.
        projects = self.home / "projects"
        try:
            paths = sorted(set(projects.glob("*/*.jsonl")) | set(projects.glob("*/*.jsonl.gz")))
        except OSError:
            paths = []
            warnings.append("프로젝트 기록 목록을 읽을 수 없습니다.")
        return paths, list(dict.fromkeys(warnings))

    def refresh_metadata(self, card):
        """Project cached registry observations; no I/O or PID liveness inference."""
        entry = self.registry.get(card["id"])
        if entry:
            status = entry["status"] or "상태 값 없음"
            file_time = datetime.fromtimestamp(entry["mtime"] / 1e9, timezone.utc).isoformat()
            provenance = f"Claude 세션 레지스트리: {status} (파일 수정 시각 {file_time}; 현재 실행 여부 미확인)"
            observed = entry["observed_at"]
        else:
            detail = "등록 정보 없음" if self.registry_available else "일부 등록 정보 접근·해석 불가"
            provenance = f"Claude 세션 레지스트리: {detail} (현재 실행 여부 미확인)"
            observed = self.registry_observed_at
        card["live"] = {"state": "unknown", "provenance": provenance, "observed_at": observed}

    def file_id(self, path):
        name = path.name.removesuffix(".gz").removesuffix(".jsonl")
        return self.clean(name, 200)

    @staticmethod
    def _active_branch(session):
        active, current = set(), session.leaf
        broken = False
        while current and current not in active:
            active.add(current)
            record = session.records_by_uuid.get(current)
            if not record:
                broken = True
                break
            current = record.get("parentUuid") or record.get("logicalParentUuid")
        if current in active:
            broken = True
        # Only ancestry-confirmed evidence is exported. This is conservative for
        # sibling parallel tool records; excluding them is safer than attributing
        # a discarded branch's answer to the active session.
        # Parallel tool calls/results legitimately fork parentUuid. Only human
        # prompts and plain answers establish conversational branch changes.
        anchors = set()
        for event in session.events:
            uid = event.get("uuid")
            if event["kind"] == "U" and event.get("from_record"):
                anchors.add(uid)
            elif event["kind"] == "A":
                content = (session.records_by_uuid.get(uid, {}).get("message") or {}).get("content")
                has_tool = isinstance(content, list) and any(isinstance(block, dict) and block.get("type") == "tool_use"
                                                            for block in content)
                if not has_tool:
                    anchors.add(uid)
        abandoned = sorted(str(uid) for uid in anchors if uid and uid not in active)
        lineage = hashlib.sha256(json.dumps(abandoned, ensure_ascii=False).encode()).hexdigest()
        return active, lineage, broken

    def read(self, path, checkpoints=()):
        data, file_stat, observation = self.bounded(path, checkpoints=checkpoints)
        warnings, records, malformed = [], [], 0
        # The sibling quick_meta(max_bytes=...) does not enforce its argument.
        # Metadata is scanned only from bytes already bounded above, never by
        # passing the source path to quick_meta or Session.
        for line in data.splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError("non-object record")
                records.append(record)
            except (ValueError, UnicodeError, RecursionError):
                malformed += 1
        if not records:
            observation["failure"] = "parse"
            raise SourceError("해석할 수 있는 세션 기록이 없습니다.", observation)
        if malformed:
            warnings.append(f"손상되었거나 아직 기록 중인 줄 {malformed}개를 제외했습니다.")
        with tempfile.TemporaryDirectory(prefix="session-dashboard-record-") as tmp:
            target = Path(tmp) / "snapshot.jsonl"
            with open(target, "xb") as stream:
                os.chmod(target, 0o600)
                stream.write(data)
            self.metrics["parse_calls"] += 1
            self.metrics["metadata_reads"] += 1
            try:
                session = self.parser.Session(target, include_thinking=False)
            except (ValueError, TypeError, KeyError, AttributeError, RecursionError) as exc:
                observation["failure"] = "parse"
                raise SourceError("기록의 구조를 해석할 수 없습니다.", observation) from exc
        try:
            sid = self.file_id(path)
            active, lineage, broken = self._active_branch(session)
            if broken:
                warnings.append("활성 분기의 부모 연결이 불완전합니다. 확인된 기록만 표시합니다.")
            titles = {}
            for row in records:
                for key in ("customTitle", "agentName"):
                    if key in row:
                        titles[key] = self.clean(row[key], 240)
            self.transcript_titles[sid] = titles
            self._title(sid)
            subagent = any(bool(row.get("isSidechain") or row.get("agentId")) for row in records)
            active_records = [row for row in records if row.get("uuid") in active]
            cwd = next((row["cwd"] for row in reversed(active_records)
                        if isinstance(row.get("cwd"), str) and row["cwd"].strip()), None)
            # A record without a cwd stays unassigned, including a renamed folder.
            last_activity = next((row["timestamp"] for row in reversed(active_records)
                                  if isinstance(row.get("timestamp"), str)), None)
            events, omitted_chars, excluded = [], 0, 0
            names = {"U": "user", "A": "assistant", "C": "compaction", "T": "tool"}
            for event in session.events:
                kind = event["kind"]
                record = session.records_by_uuid.get(event.get("uuid"), {})
                if kind not in names or event.get("uuid") not in active or record.get("type") == "attachment":
                    excluded += 1
                    continue
                if kind in {"U", "A"}:
                    raw = str(event["text"])
                    if re.match(r"(?is)^\s*(?:#\s*(?:AGENTS\.md|CLAUDE\.md)\s+instructions|<system-reminder\b|<instructions\b|<environment_context\b)", raw):
                        excluded += 1
                        continue
                    text = self.clean(raw)
                    omitted_chars += max(0, len(self.parser.redact(raw)) - self.text_limit)
                elif kind == "C":
                    text = "기록이 압축되었습니다." if event.get("boundary") else "압축 요약이 기록되었습니다. 본문은 표시하지 않습니다."
                else:
                    tool = self.clean(event.get("tool", "unknown"), 100)
                    result = event.get("result")
                    status = "미확인" if result is None else ("중단" if result.get("interrupted") else
                             "백그라운드" if result.get("background") else "실패" if result.get("error") else "반환 기록 있음")
                    text = f"도구 {tool}: {status}"
                    if event.get("tool") in {"Write", "Edit", "MultiEdit", "NotebookEdit"}:
                        inputs = event.get("input") or {}
                        filename = (inputs.get("file_path") or inputs.get("notebook_path")) if isinstance(inputs, dict) else None
                        if filename:
                            text = self.clean(text + " · 파일 " + str(filename))
                events.append({"id": str(event["n"]), "kind": names[kind],
                               "timestamp": self.clean(event.get("ts"), 80) or None, "text": text})
            parse_errors = sum(event["kind"] == "N" and event["text"].startswith("[parse error") for event in session.events)
            if parse_errors:
                warnings.append(f"형식이 맞지 않는 이벤트 {parse_errors}개를 제외했습니다.")
            if not active:
                warnings.append("활성 분기를 식별할 UUID가 없어 근거를 표시하지 않습니다.")
            selected = set(range(max(0, len(events) - self.evidence_limit), len(events)))
            users = [i for i, event in enumerate(events) if event["kind"] == "user"]
            compactions = [i for i, event in enumerate(events) if event["kind"] == "compaction"]
            anchors = set(users[:1] + users[-1:] + compactions[-1:])
            selected.update(anchors)
            while len(selected) > self.evidence_limit:
                selected.remove(min(selected - anchors))
            evidence = [events[i] for i in sorted(selected)]
            observation["logical"]["lineage"] = lineage
            revision = {**observation["logical"], "identity": list(file_stat[:2])}
            first = next((event["text"] for event in events if event["kind"] == "user"), "")
            last_record = next((row for row in reversed(active_records) if row.get("type") in {"user", "assistant"}), {})
            stop_reason = (last_record.get("message") or {}).get("stop_reason")
            recorded_turn = {"end_turn": "응답 턴 종료 기록 있음", "tool_use": "도구 호출 기록 있음",
                             "max_tokens": "출력 한도 도달 기록 있음"}.get(stop_reason, "불명")
            return {"id": sid, "cwd": self.clean(cwd, 2000) if cwd else None,
                    "scope_cwd": str(Path(cwd).expanduser().resolve()) if cwd else None,
                    "subagent": subagent, "automatic_title": re.sub(r"\s+", " ", first)[:100],
                    "live": {"state": "unknown", "provenance": "transcript", "observed_at": None},
                    "recorded_turn": recorded_turn, "last_activity": self.clean(last_activity, 80) or None,
                    "revision": revision, "events": events[-self.recent_limit:], "evidence": evidence,
                    "warnings": warnings[:20],
                    "truncation": {"recent_events": max(0, len(events) - self.recent_limit),
                                   "evidence_events": max(0, len(events) - len(evidence)),
                                   "text_characters": omitted_chars, "excluded_events": excluded},
                    "source_mtime": file_stat[3] / 1e9, "_observation": observation}
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            observation["failure"] = "parse"
            raise SourceError("inspect-session 파서의 반환 형식이 호환되지 않습니다.", observation) from exc
