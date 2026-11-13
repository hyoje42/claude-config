#!/usr/bin/env python3
"""Synthetic view-model, document, export and HTTP contracts; not browser tests."""

import hashlib
import http.client
import importlib.util
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from html.parser import HTMLParser
from pathlib import Path

sys.dont_write_bytecode = True
SKILL = Path(__file__).resolve().parents[1] / "home/skills/session-dashboard"
SCRIPT = SKILL / "scripts/dashboard.py"
JAVASCRIPT = SKILL / "assets/dashboard.js"
spec = importlib.util.spec_from_file_location("dashboard_ui_contract", SCRIPT)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.elements = []
        self.scripts = []
        self.styles = []
        self.current = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs))
        if tag in {"script", "style"}:
            item = {"attrs": attrs, "text": ""}
            (self.scripts if tag == "script" else self.styles).append(item)
            self.current = item

    def handle_endtag(self, tag):
        if tag in {"script", "style"}:
            self.current = None

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data


def session(sid, status="fresh", attention=False, last="2026-11-12T03:00:00Z"):
    captured = {"id": "7", "kind": "user", "timestamp": last, "text": "입력 당시의 근거입니다."}
    summary = None if status == "missing" else {
        "status": status, "snapshot_id": "input-" + sid, "session_id": sid,
        "fields": {"goal": [{"text": "검색 정렬을 수정합니다.", "refs": ["7"]}],
                   "attention": [{"text": "실패 사례를 확인해야 합니다.", "refs": ["7"]}] if attention else []},
        "evidence": [captured], "summary_at": last, "input_at": last}
    return {"id": sid, "title": "같은 이름", "title_source": "stored", "cwd": "/project/one",
            "live": {"state": "unknown", "provenance": "transcript", "observed_at": None},
            "recorded_turn": "완료", "last_activity": last, "collected_at": last,
            "summary_at": last if summary else None, "summary": summary,
            "events": [{**captured, "text": "현재 수집된 다른 내용입니다."}],
            "evidence": [{**captured, "text": "현재 근거도 다른 내용입니다."}],
            "warnings": [], "truncation": {"recent_events": 0}}


def view(sessions):
    return {"schema": 1, "tool": "fixture-tool", "collected_at": "2026-11-12T05:00:00Z",
            "collect_seconds": 5, "selection": {"projects": ["/project/one"], "sessions": [],
            "since_hours": 24, "limit": 20, "self_exclusion": "confirmed"},
            "warnings": [], "omitted_sessions": 0, "metrics": {}, "sessions": sessions}


class ModelTests(unittest.TestCase):
    def run_model(self, body, data):
        script = ("const model = require(process.argv[1]);"
                  "const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
                  "const result = (() => {" + body + "})();"
                  "process.stdout.write(JSON.stringify(result));")
        result = subprocess.run(["node", "-e", script, str(JAVASCRIPT)],
                                input=json.dumps(data), capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_fresh_attention_precedes_recency_but_stale_attention_does_not(self):
        cards = [session("stale", "stale", True, "2026-11-11T03:00:00Z"),
                 session("newest", last="2026-11-12T04:00:00Z"),
                 session("attention", attention=True, last="2026-11-10T03:00:00Z"),
                 session("invalid", "invalid", True), session("missing", "missing")]
        result = self.run_model("return {ids: model.selectSessions(input).map(s => s.id), counts: model.counts(input)};", cards)
        self.assertEqual(result["ids"], ["attention", "newest", "invalid", "missing", "stale"])
        self.assertEqual(result["counts"], {"total": 5, "attention": 1, "outdated": 2, "missing": 1})

    def test_status_filters_are_disjoint_and_unknown_is_not_inferred_from_turn_end(self):
        cards = [session("fresh", attention=True), session("stale", "stale", True),
                 session("invalid", "invalid", True), session("missing", "missing")]
        result = self.run_model("return Object.fromEntries(['fresh','stale','invalid','missing','attention','unknown'].map(f => [f, model.selectSessions(input, '', f).map(s => s.id)]));", cards)
        for status in ("fresh", "stale", "invalid", "missing"):
            self.assertEqual(result[status], [status])
        self.assertEqual(result["attention"], ["fresh"])
        self.assertEqual(set(result["unknown"]), {"fresh", "stale", "invalid", "missing"})

    def test_search_matches_identity_path_renamed_title_and_supported_claims(self):
        cards = [session("full-session-id-one"), session("full-session-id-two")]
        cards[1]["cwd"] = "/project/two"
        results = self.run_model("""
          const ids = q => model.selectSessions(input, q).map(s => s.id);
          const both = ids('같은 이름');
          input[1].title = '새로운 이름';
          return {both, renamed: ids('새로운 이름'), identity: ids('ID-ONE'), path: ids('/project/two'), goal: ids('검색 정렬')};
        """, cards)
        self.assertEqual(results["both"], ["full-session-id-one", "full-session-id-two"])
        self.assertEqual(results["renamed"], ["full-session-id-two"])
        self.assertEqual(results["identity"], ["full-session-id-one"])
        self.assertEqual(results["path"], ["full-session-id-two"])
        self.assertEqual(len(results["goal"]), 2)

    def test_invalid_claims_are_neither_displayable_nor_searchable(self):
        card = session("invalid", "invalid", True)
        result = self.run_model("return {claims: model.claimsFor(input, 'goal'), search: model.selectSessions([input], '검색 정렬'), priority: model.needsAttention(input)};", card)
        self.assertEqual(result, {"claims": [], "search": [], "priority": False})

    def test_card_preview_shows_recorded_progress_without_claiming_current_work(self):
        reported = "설치 안내에 실행 예시를 추가했다고 보고했습니다."
        current = "추가한 실행 예시를 검증하고 있습니다."
        cards = [session("completed-only"), session("current-preferred"),
                 session("stale", "stale"), session("invalid", "invalid"), session("unknown")]
        for card in cards[:-1]:
            card["title"] = "설치 안내 정리"
            card["summary"]["fields"]["current"] = []
            card["summary"]["fields"]["completed"] = [{"text": reported, "refs": ["7"]}]
        cards[1]["summary"]["fields"]["current"] = [{"text": current, "refs": ["7"]}]
        previews = self.run_model("return Object.fromEntries(input.map(s => [s.id, model.previewFields(s)]));", cards)
        self.assertEqual(previews["completed-only"][1],
                         {"key": "completed", "label": "기록된 진행", "known": True, "text": reported})
        self.assertEqual(previews["current-preferred"][1],
                         {"key": "current", "label": "현재 작업", "known": True, "text": current})
        self.assertEqual(previews["stale"][1],
                         {"key": "completed", "label": "이전 요약 · 기록된 진행", "known": True, "text": reported})
        self.assertTrue(all(field["label"].startswith("이전 요약 · ") for field in previews["stale"]))
        self.assertEqual(previews["invalid"], [])
        self.assertEqual(previews["unknown"][1]["key"], "current")
        self.assertFalse(previews["unknown"][1]["known"])
        self.assertIn("알 수 없음", previews["unknown"][1]["text"])

    def test_evidence_uses_captured_snapshot_even_when_current_ids_are_reused(self):
        card = session("stale", "stale")
        result = self.run_model("return model.resolveEvidence(input, ['7', 'absent']);", card)
        self.assertEqual(result[0]["text"], "입력 당시의 근거입니다.")
        self.assertEqual(result[1]["kind"], "missing")
        self.assertNotIn("현재", result[1]["text"])

    def test_warning_filter_includes_truncation_without_a_warning_message(self):
        cards = [session("normal"), session("truncated")]
        cards[1]["truncation"]["text_characters"] = 12
        result = self.run_model("return model.selectSessions(input, '', 'warning').map(s => s.id);", cards)
        self.assertEqual(result, ["truncated"])

    def test_polling_uses_collection_interval_and_bounded_backoff(self):
        result = self.run_model("return [model.pollDelay(.1), model.pollDelay(7), model.pollDelay(7, 1), model.pollDelay(30, 2), model.pollDelay(3600)];", {})
        self.assertEqual(result, [100, 7000, 14000, 60000, 3600000])


class DocumentTests(unittest.TestCase):
    def test_online_document_uses_accessible_controls_and_same_origin_assets(self):
        document = Document(dashboard.render_html().decode())
        ids = {attrs.get("id"): (tag, attrs) for tag, attrs in document.elements if attrs.get("id")}
        self.assertEqual(ids["search"][1]["type"], "search")
        self.assertEqual(ids["status-filter"][0], "select")
        self.assertEqual(ids["refresh"][0], "button")
        self.assertEqual(ids["summary-help"][1]["aria-controls"], "summary-guide")
        labels = {attrs.get("for") for tag, attrs in document.elements if tag == "label"}
        self.assertTrue({"search", "status-filter"}.issubset(labels))
        self.assertEqual([(script["attrs"].get("src"), script["text"]) for script in document.scripts], [("/dashboard.js", "")])
        self.assertEqual([attrs["href"] for tag, attrs in document.elements if tag == "link"], ["/dashboard.css"])
        self.assertFalse(document.styles)
        self.assertFalse(any(key.startswith("on") for _, attrs in document.elements for key in attrs))

    def test_offline_document_embeds_data_before_code_and_escapes_script_boundaries(self):
        card = session("unsafe")
        unsafe = '</script><script>window.INJECTED=1</script><img src="https://example.invalid" onerror="alert(1)">&\u2028\u2029'
        card["title"] = unsafe
        card["summary"]["fields"]["goal"][0]["text"] = unsafe
        state = view([card])
        text = dashboard.render_html(state).decode()
        document = Document(text)
        self.assertEqual(len(document.scripts), 2)
        self.assertEqual(document.scripts[0]["attrs"], {"id": "dashboard-data", "type": "application/json"})
        self.assertEqual(json.loads(document.scripts[0]["text"]), state)
        self.assertEqual(document.scripts[1]["text"], JAVASCRIPT.read_text())
        self.assertEqual(len(document.styles), 1)
        self.assertNotIn(unsafe, text)
        self.assertIn("\\u003c/script\\u003e", text)
        self.assertFalse(any("src" in attrs for _, attrs in document.elements))
        self.assertFalse(any(tag == "link" for tag, _ in document.elements))
        self.assertFalse(any(tag in {"iframe", "img", "object"} for tag, _ in document.elements))
        css = document.styles[0]["text"]
        self.assertNotIn("@import", css)
        self.assertNotIn("url(", css)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="dashboard-ui-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "home"
        sessions = self.home / "projects" / "fixture-project"
        sessions.mkdir(parents=True)
        self.project = self.root / "project"
        self.project.mkdir()
        self.runtime = self.root / "runtime"
        self.sid = "11111111-2222-4333-8444-555555555555"
        self.path = sessions / (self.sid + ".jsonl")
        timestamp = dashboard.now()
        rows = [{"timestamp": timestamp, "type": "user", "uuid": "user-1", "parentUuid": None,
                 "sessionId": self.sid, "cwd": str(self.project),
                 "message": {"role": "user", "content": [{"type": "text", "text": "검색 정렬을 수정해 주세요."}]}}]
        self.path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        self.original_hash = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.source = dashboard.load_source()
        self.options = ["--home", str(self.home), "--project", str(self.project),
                        "--runtime-dir", str(self.runtime), "--self", "observer"]
        args = dashboard.parser(self.source).parse_args([*self.options, "summary-input"])
        self.config = dashboard.configuration(args, self.source)

    def cli(self, *args):
        result = subprocess.run([sys.executable, "-I", "-B", str(SCRIPT), *self.options, *args],
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_cli_summary_and_offline_export_preserve_source_and_evidence(self):
        snapshot = self.cli("summary-input")["inputs"][0]
        payload = self.root / "summary.json"
        payload.write_text(json.dumps({"session_id": self.sid, "snapshot_id": snapshot["snapshot_id"],
                           "fields": {"goal": [{"text": "검색 결과의 순서를 수정합니다.",
                                                "refs": [snapshot["evidence"][0]["id"]]}]}}, ensure_ascii=False))
        self.assertEqual(self.cli("summary-import", "--input", str(payload))["status"], "fresh")
        output = self.root / "dashboard.html"
        self.cli("export", "--output", str(output))
        exported = Document(output.read_text())
        state = json.loads(exported.scripts[0]["text"])
        self.assertEqual(state["sessions"][0]["summary"]["snapshot_id"], snapshot["snapshot_id"])
        self.assertEqual(state["sessions"][0]["summary"]["evidence"], snapshot["evidence"])
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.runtime / "registry.json").exists())
        self.assertEqual(hashlib.sha256(self.path.read_bytes()).hexdigest(), self.original_hash)

    def test_http_asset_routes_and_authenticated_state(self):
        adapter = self.source.Adapter(self.config["home"], self.config["max_bytes"])
        store = dashboard.SummaryStore(self.runtime, adapter.clean)
        collector = dashboard.Collector(self.config, self.source, store)
        registry = {"token": "a" * 64, "instance_id": "fixture", "config_id": self.config["config_id"]}
        server = dashboard.make_server(self.config, collector, store, registry)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": .05}, daemon=True)
        thread.start()
        try:
            def request(path, auth=False):
                client = http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=3)
                try:
                    client.request("GET", path, headers={"Authorization": "Bearer " + registry["token"]} if auth else {})
                    response = client.getresponse()
                    return response.status, dict(response.getheaders()), response.read()
                finally:
                    client.close()

            for route, mime, filename in (("/", "text/html", "index.html"), ("/dashboard.css", "text/css", "dashboard.css"),
                                          ("/dashboard.js", "text/javascript", "dashboard.js")):
                status, headers, data = request(route)
                self.assertEqual(status, 200)
                self.assertIn(mime, headers["Content-Type"])
                self.assertEqual(data, (SKILL / "assets" / filename).read_bytes())
                self.assertIn("script-src 'self'", headers["Content-Security-Policy"])
            self.assertEqual(request("/api/state")[0], 401)
            self.assertEqual(request("/scripts/source.py")[0], 404)
            status, _, data = request("/api/state", True)
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data)["sessions"][0]["id"], self.sid)
            self.assertNotIn(registry["token"].encode(), data)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)
        self.assertFalse(thread.is_alive())


if __name__ == "__main__":
    unittest.main(verbosity=2)
