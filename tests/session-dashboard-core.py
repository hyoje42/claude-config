#!/usr/bin/env python3
"""Synthetic, read-only source and real subprocess/HTTP checks for the dashboard."""

import concurrent.futures
import contextlib
import copy
import gzip
import hashlib
import http.client
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).resolve().parents[1] / "home/skills/session-dashboard/scripts/dashboard.py"
spec = importlib.util.spec_from_file_location("dashboard", SCRIPT)
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
source = dashboard.load_source()
SID = "11111111-1111-4111-8111-111111111111"
OTHER = "11111111-1111-4111-8111-222222222222"
THIRD = "33333333-3333-4333-8333-333333333333"


def record(kind, **payload):
    return {"timestamp": dashboard.now(), "type": kind, **payload}


def message(role, text, **extra):
    return record(role, uuid=str(uuid.uuid4()),
                  message={"role": role, "content": [{"type": "text", "text": text}]}, **extra)


def chain(rows, parent):
    output = []
    for row in rows:
        row = copy.deepcopy(row)
        if row.get("type") in {"user", "assistant", "system"}:
            row.setdefault("uuid", str(uuid.uuid4()))
            row.setdefault("parentUuid", parent)
            parent = row["uuid"]
        output.append(row)
    return output


def encoded(rows):
    return ("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n").encode()


class CoreTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="session-dashboard-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.home = self.root / "tool-home"
        self.home.mkdir()
        self.project = self.root / "project"
        self.project.mkdir()
        self.runtime = self.root / "runtime"
        self.config = self.configuration()

    def configuration(self, *extra):
        args = dashboard.parser(source).parse_args([
            "--home", str(self.home), "--project", str(self.project),
            "--runtime-dir", str(self.runtime), "--self", "observer", *extra, "summary-input"])
        return dashboard.configuration(args, source)

    def write(self, rows=None, sid=SID, cwd=True, compressed=False):
        directory = self.home / "projects" / "escaped-project-name"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{sid}.jsonl"
        meta = record("system", uuid="root-" + sid, parentUuid=None, subtype="fixture")
        if cwd is not None:
            meta["cwd"] = str(self.project) if cwd is True else str(cwd)
        data = encoded([meta, *chain(rows or [], meta["uuid"])])
        if compressed:
            path = path.with_suffix(".jsonl.gz")
            path.write_bytes(gzip.compress(data))
        else:
            path.write_bytes(data)
        return path

    def append_data(self, path, rows):
        data = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
        previous = [json.loads(line) for line in data.splitlines() if line.strip()]
        parent = next((row["uuid"] for row in reversed(previous)
                       if row.get("type") in {"user", "assistant", "system"} and row.get("uuid")), None)
        return encoded(chain(rows, parent))

    def append(self, path, rows):
        data = self.append_data(path, rows)
        with path.open("ab") as stream:
            stream.write(gzip.compress(data, mtime=1) if path.suffix == ".gz" else data)

    def registry(self, sid=SID, **values):
        directory = self.home / "sessions"
        directory.mkdir(exist_ok=True)
        path = directory / (sid + ".json")
        path.write_text(json.dumps({"sessionId": sid, **values}))
        return path

    def collector(self, config=None):
        config = config or self.config
        adapter = source.Adapter(config["home"], config["max_bytes"])
        store = dashboard.SummaryStore(Path(config["runtime_dir"]), adapter.clean)
        return dashboard.Collector(config, source, store)

    def payload(self, snapshot, text="요청한 작업을 진행합니다.", ref=None):
        return {"session_id": snapshot["session_id"], "snapshot_id": snapshot["snapshot_id"],
                "fields": {"goal": [{"text": text, "refs": [ref or snapshot["evidence"][0]["id"]]}]}}

    @contextlib.contextmanager
    def held_collection(self, collector, before_read=False, checkpoints=True):
        """Pause a real collector while a separate thread/process competes."""
        entered, release = threading.Event(), threading.Event()
        original_read = collector.adapter.read

        def hold():
            entered.set()
            if not release.wait(10):
                raise AssertionError("collection barrier timed out")

        def read(path, sizes=()):
            if before_read:
                hold()
            try:
                return original_read(path, sizes if checkpoints else ())
            finally:
                if not before_read:
                    hold()

        with patch.object(collector.adapter, "read", side_effect=read):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(collector.collect)
                try:
                    self.assertTrue(entered.wait(5), "collector never reached the read barrier")
                    yield future, release
                finally:
                    release.set()


    @contextlib.contextmanager
    def competing_cli(self, config, *arguments):
        """Run the actual CLI, exposing entry before/after its collection lock."""
        with tempfile.TemporaryDirectory(prefix="cli-barrier-", dir=self.root) as temporary:
            ready, entered = Path(temporary) / "ready", Path(temporary) / "entered"
            program = '''
import importlib.util
import sys
from pathlib import Path
spec = importlib.util.spec_from_file_location("dashboard", sys.argv[1])
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)
collect, inner = dashboard.Collector.collect, dashboard.Collector._collect
def attempt(self, *args, **kwargs):
    Path(sys.argv[2]).touch()
    return collect(self, *args, **kwargs)
def acquired(self, *args, **kwargs):
    Path(sys.argv[3]).touch()
    return inner(self, *args, **kwargs)
dashboard.Collector.collect = attempt
dashboard.Collector._collect = acquired
raise SystemExit(dashboard.main(sys.argv[4:]))
'''
            command = [sys.executable, "-I", "-B", "-c", program, str(SCRIPT), str(ready), str(entered),
                       "--home", config["home"], "--project", str(self.project),
                       "--runtime-dir", config["runtime_dir"], "--self", "observer", *arguments]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                deadline = time.monotonic() + 5
                while not ready.exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue(ready.exists(), "CLI never attempted collection")
                yield process, entered
            finally:
                if process.poll() is None:
                    process.terminate()
                process.communicate(timeout=5)


    def assert_cli_waiting(self, process, entered):
        with self.assertRaises(subprocess.TimeoutExpired):
            process.wait(timeout=0.2)
        self.assertFalse(entered.exists(), "another process entered the collection transaction")


    def test_runtime_transaction_excludes_cli_until_observation_is_saved(self):
        path = self.write([message("user", "T1 request")], compressed=True)
        original = path.read_bytes()
        collector = self.collector()
        initial = collector.collect()["sessions"][0]
        accepted, pending = collector.store.issue_many([initial, initial])
        collector.store.accept(self.payload(accepted), {SID: initial})
        recompressed = gzip.compress(gzip.decompress(original), mtime=1)
        path.write_bytes(recompressed)
        payload = self.root / "concurrent-pending.json"
        payload.write_text(json.dumps(self.payload(pending)))
        with self.held_collection(collector) as (first, release):
            with path.open("ab") as stream:
                stream.write(b"incomplete tail RAW_PRIVATE_SYNTHETIC_SENTINEL")
            with self.competing_cli(self.config, "export", "--output", str(self.root / "contending.html")) as (process, entered):
                self.assert_cli_waiting(process, entered)
                release.set()
                self.assertEqual(first.result(timeout=5)["sessions"][0]["summary"]["status"], "fresh")
                stdout, stderr = process.communicate(timeout=5)
                self.assertEqual(process.returncode, 0, stdout + stderr)
        self.assertFalse(collector.store.read()["invalid_snapshots"])
        path.write_bytes(recompressed)
        with self.competing_cli(self.config, "summary-import", "--input", str(payload)) as (process, entered):
            stdout, stderr = process.communicate(timeout=5)
            self.assertEqual(process.returncode, 0, stdout + stderr)
            self.assertEqual(json.loads(stdout)["status"], "fresh")
        public = (self.root / "contending.html").read_text() + collector.store.path.read_text()
        self.assertNotIn("_raw_baseline", public)
        self.assertNotIn("RAW_PRIVATE_SYNTHETIC_SENTINEL", public)


    def test_discontinuities_survive_filters_parse_failures_and_fresh_collectors(self):
        modes = ("empty", "unparseable", "limit", "project", "missing_discovery",
                 "rename_back", "same_inode_recreation", "new_inode_recreation", "replacement_unparseable")
        for mode in modes:
            with self.subTest(mode=mode):
                path = self.write([message("user", "original request"), message("assistant", "original progress")])
                original = path.read_bytes()
                config = self.configuration("--limit", "1")
                issuer = self.collector(config)
                card = issuer.collect()["sessions"][0]
                accepted, pending = issuer.store.issue_many([card, card])
                issuer.store.accept(self.payload(accepted), {SID: card})
                other = away = replacement = None
                if mode == "empty":
                    path.write_bytes(b"")
                elif mode == "unparseable":
                    path.write_bytes(b'{"type":["unhashable-record-type"]}\n')
                elif mode == "limit":
                    path.write_bytes(original.replace(b"original progress", b"replaced progress"))
                    other = self.write([message("user", "newest request")], sid=OTHER)
                elif mode == "project":
                    elsewhere = self.root / "elsewhere"
                    elsewhere.mkdir(exist_ok=True)
                    path.write_bytes(original.replace(str(self.project).encode(), str(elsewhere).encode()))
                elif mode == "rename_back":
                    away = path.with_suffix(".hidden")
                    path.rename(away)
                elif mode == "same_inode_recreation":
                    away = path.with_suffix(".retained")
                    os.link(path, away)
                    path.unlink()
                elif mode == "new_inode_recreation":
                    replacement = path.with_suffix(".replacement")
                    replacement.write_bytes(original)
                    self.assertNotEqual(path.stat().st_ino, replacement.stat().st_ino)
                    path.unlink()
                elif mode == "replacement_unparseable":
                    replacement = path.with_suffix(".replacement")
                    replacement.write_bytes(b'{"type":["unhashable-record-type"]}\n')
                    os.replace(replacement, path)
                    replacement = None
                else:
                    path.unlink()
                observer = self.collector(config)
                if mode == "missing_discovery":
                    with patch.object(observer.adapter, "discover", return_value=([], ["일시적인 목록 오류"])):
                        intermediate = observer.collect(True)
                else:
                    intermediate = observer.collect(True)
                if mode in {"empty", "project", "missing_discovery", "rename_back", "same_inode_recreation", "new_inode_recreation"}:
                    self.assertEqual(intermediate["sessions"], [])
                if mode == "limit":
                    self.assertEqual(intermediate["sessions"][0]["id"], OTHER)
                invalid = observer.store.read()["invalid_snapshots"]
                self.assertIn(accepted["snapshot_id"], invalid)
                self.assertIn(pending["snapshot_id"], invalid)
                if mode == "same_inode_recreation":
                    os.link(away, path)
                    self.assertEqual(list(source.signature(path)[:2]), accepted["source_revision"]["identity"])
                    away.unlink()
                elif away is not None:
                    away.rename(path)
                elif replacement is not None:
                    replacement.rename(path)
                else:
                    path.write_bytes(original)
                if other is not None:
                    other.unlink()
                reloaded = self.collector(config)
                restored = reloaded.collect(True)["sessions"][0]
                self.assertEqual(restored["summary"]["status"], "invalid")
                with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
                    reloaded.store.accept(self.payload(pending), {SID: restored})
                public = json.dumps(restored)
                self.assertNotIn(str(path), public)
                self.assertNotIn(str(path), json.dumps(accepted))


    def test_discovery_and_read_errors_do_not_permanently_invalidate_sources(self):
        path = self.write([message("user", "original goal")])
        issuer = self.collector()
        card = issuer.collect()["sessions"][0]
        accepted, pending = issuer.store.issue_many([card, card])
        issuer.store.accept(self.payload(accepted), {SID: card})
        for mode in ("omitted", "discovery_error", "stat_error", "read_error", "unavailable_probe"):
            with self.subTest(mode=mode):
                observer = self.collector()
                if mode == "omitted":
                    with patch.object(observer.adapter, "discover", return_value=([], ["목록 불완전"])):
                        observer.collect(True)
                elif mode == "discovery_error":
                    with patch.object(observer.adapter, "discover", side_effect=PermissionError("blocked")):
                        observer.collect(True)
                elif mode == "stat_error":
                    with patch.object(source, "signature", side_effect=PermissionError("blocked")):
                        observer.collect(True)
                elif mode == "read_error":
                    with patch.object(observer.adapter, "read", side_effect=source.SourceError("일시적인 읽기 오류")):
                        observer.collect(True)
                else:
                    with patch.object(observer.adapter, "discover", return_value=([], [])), patch.object(observer, "_probe", return_value=(None, False)):
                        observer.collect(True)
                self.assertNotIn(accepted["snapshot_id"], observer.store.read()["invalid_snapshots"])
                self.assertNotIn(pending["snapshot_id"], observer.store.read()["invalid_snapshots"])
        fresh = self.collector()
        current = fresh.collect()["sessions"][0]
        self.assertEqual(current["summary"]["status"], "fresh")
        self.assertEqual(fresh.store.accept(self.payload(pending), {SID: current})["status"], "fresh")
        with path.open("ab") as stream:
            stream.write(b'{"partial":')
        stale = fresh.collect()["sessions"][0]
        self.assertEqual(stale["summary"]["status"], "stale")
        metrics = dict(fresh.adapter.metrics)
        fresh.collect()
        self.assertEqual(fresh.adapter.metrics, metrics)


    def test_bounded_error_proofs_detect_same_size_larger_and_gzip_rewrites(self):
        for mode in ("same_size", "larger", "gzip"):
            with self.subTest(mode=mode):
                sid = {"same_size": SID, "larger": OTHER, "gzip": THIRD}[mode]
                path = self.write([message("user", "original request"), message("assistant", "original progress")], sid=sid, compressed=mode == "gzip")
                config = self.configuration("--session", sid)
                original = path.read_bytes()
                issuer = self.collector(config)
                card = issuer.collect()["sessions"][0]
                accepted, pending = issuer.store.issue_many([card, card])
                issuer.store.accept(self.payload(accepted), {sid: card})
                if mode == "gzip":
                    broken = b"BAD" + original[3:]
                else:
                    broken = b'{"type":["unhashable-record-type"],"private":"RAW_PRIVATE_BODY"}\n'
                    broken += b" " * (len(original) - len(broken) + (100 if mode == "larger" else 0))
                path.write_bytes(broken)
                adapter = source.Adapter(self.home, self.config["max_bytes"])
                with self.assertRaises(source.SourceError) as failure:
                    adapter.read(path, [card["revision"]["size"], len(original)])
                proof = failure.exception.observation
                self.assertEqual(proof["raw"]["digest"], hashlib.sha256(broken).hexdigest())
                self.assertEqual(proof["raw"]["size"], len(broken))
                self.assertEqual(adapter.metrics["read_calls"], 1)
                self.assertEqual(adapter.metrics["read_bytes"], len(broken))
                self.assertEqual(proof["failure"], "decode" if mode == "gzip" else "parse")
                if mode == "gzip":
                    self.assertIsNone(proof["logical"])
                    self.assertEqual(adapter.metrics["parse_calls"], 0)
                else:
                    self.assertEqual(proof["logical"]["digest"], hashlib.sha256(broken).hexdigest())
                    self.assertEqual(adapter.metrics["parse_calls"], 1)
                observer = self.collector(config)
                view = observer.collect()
                self.assertIsNone(view["sessions"][0]["revision"])
                self.assertNotIn("_observation", json.dumps(view))
                self.assertNotIn("RAW_PRIVATE_BODY", observer.store.path.read_text())
                self.assertIn(pending["snapshot_id"], observer.store.read()["invalid_snapshots"])
                metrics = dict(observer.adapter.metrics)
                observer.collect()
                self.assertEqual(observer.adapter.metrics, metrics)
                path.write_bytes(original)
                restored = self.collector(config)
                current = restored.collect()["sessions"][0]
                self.assertEqual(current["summary"]["status"], "invalid")
                with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
                    restored.store.accept(self.payload(pending), {sid: current})


    def test_observed_append_then_rollback_survives_plain_and_compressed_reloads(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                sid = OTHER if compressed else SID
                path = self.write([message("user", "request"), message("assistant", "progress")], sid=sid, compressed=compressed)
                config = self.configuration("--session", sid)
                original = gzip.decompress(path.read_bytes()) if compressed else path.read_bytes()
                issuer = self.collector(config)
                card = issuer.collect()["sessions"][0]
                accepted, pending = issuer.store.issue_many([card, card])
                issuer.store.accept(self.payload(accepted), {sid: card})
                if compressed:
                    path.write_bytes(gzip.compress(original, compresslevel=1, mtime=1))
                    recompressed = self.collector(config).collect()["sessions"][0]
                    self.assertEqual(recompressed["summary"]["status"], "fresh")
                extended = original + self.append_data(path, [message("assistant", "observed later progress")])
                compressed_append = gzip.compress(original, mtime=2) + gzip.compress(extended[len(original):], mtime=2)
                path.write_bytes(compressed_append if compressed else extended)
                observer = self.collector(config)
                current = observer.collect()["sessions"][0]
                self.assertEqual(current["summary"]["status"], "stale")
                source_key = card["revision"]["source_key"]
                latest = observer.store.read()["observations"][source_key]
                self.assertEqual(latest["logical"]["size"], len(extended))
                self.assertEqual(latest["logical"]["digest"], hashlib.sha256(extended).hexdigest())
                self.assertNotIn("prefixes", json.dumps(latest))
                self.assertIn(len(extended), set().union(*observer.store.checkpoints().values()))
                metrics = dict(observer.adapter.metrics)
                observer.collect()
                self.assertEqual(observer.adapter.metrics, metrics)
                path.write_bytes(gzip.compress(original, mtime=3) if compressed else original)
                restored = self.collector(config)
                current = restored.collect()["sessions"][0]
                self.assertEqual(current["summary"]["status"], "invalid")
                with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
                    restored.store.accept(self.payload(pending), {sid: current})


    def test_missing_checkpoints_and_delayed_observations_do_not_prove_rewinds(self):
        path = self.write([message("user", "initial request")])
        issuer = self.collector()
        card = issuer.collect()["sessions"][0]
        snapshot = issuer.store.issue(card)
        issuer.store.accept(self.payload(snapshot), {SID: card})
        source_key = card["revision"]["source_key"]
        early = {**copy.deepcopy(issuer.cache[path][1]["_observation"]),
                 "source_key": source_key, "path": str(path), "session_id": SID}
        self.append(path, [message("assistant", "normal append")])
        reader = source.Adapter(self.home, self.config["max_bytes"])
        without_checkpoints = reader.read(path)["_observation"]
        issuer.store.observe([{**without_checkpoints, "source_key": source_key, "path": str(path), "session_id": SID}])
        self.assertFalse(issuer.store.read()["invalid_snapshots"])
        self.assertEqual(issuer.store.read()["observations"][source_key]["logical"]["size"], card["revision"]["size"])
        self.assertEqual(issuer.store.read()["latest_observations"][source_key]["logical"]["size"], path.stat().st_size)
        middle = {**copy.deepcopy(without_checkpoints), "source_key": source_key, "path": str(path), "session_id": SID}
        self.append(path, [message("assistant", "next append without earlier checkpoints")])
        newest = reader.read(path)["_observation"]
        issuer.store.observe([{**newest, "source_key": source_key, "path": str(path), "session_id": SID}])
        latest_unconfirmed = copy.deepcopy(issuer.store.read()["latest_observations"][source_key])
        self.assertGreater(middle["observed_ns"], issuer.store.read()["observations"][source_key]["observed_ns"])
        self.assertLess(middle["observed_ns"], latest_unconfirmed["observed_ns"])
        issuer.store.observe([middle])
        self.assertFalse(issuer.store.read()["invalid_snapshots"])
        self.assertEqual(issuer.store.read()["latest_observations"][source_key], latest_unconfirmed)
        observer = self.collector()
        self.assertEqual(observer.collect()["sessions"][0]["summary"]["status"], "stale")
        latest = copy.deepcopy(observer.store.read()["observations"][source_key])
        observer.store.observe([early])
        self.assertEqual(observer.store.read()["observations"][source_key], latest)
        early["observed_ns"] = time.time_ns()
        observer.store.observe([early])
        self.assertEqual(observer.store.read()["observations"][source_key], latest)
        self.assertFalse(observer.store.read()["invalid_snapshots"])


    def test_serialized_checkpoint_reads_keep_append_history_and_detect_later_shrink(self):
        for compressed in (False, True):
            with self.subTest(compressed=compressed):
                self.home = self.root / ("checkpoint-home-" + str(compressed))
                self.home.mkdir()
                config = self.configuration("--runtime-dir", str(self.root / ("checkpoint-" + str(compressed))))
                path = self.write([message("user", "T1 request")], compressed=compressed)
                collector = self.collector(config)
                initial = collector.collect()["sessions"][0]
                accepted, pending = collector.store.issue_many([initial, initial])
                collector.store.accept(self.payload(accepted), {SID: initial})

                def append_progress(label):
                    data = self.append_data(path, [message("assistant", label)])
                    with path.open("ab") as stream:
                        stream.write(gzip.compress(data, mtime=1) if compressed else data)

                append_progress("T2 progress")
                t2 = path.read_bytes()
                output = self.root / ("append-" + str(compressed) + ".html")
                with self.held_collection(collector) as (first, release):
                    append_progress("T3 progress")
                    t3 = path.read_bytes()
                    with self.competing_cli(config, "export", "--output", str(output)) as (process, entered):
                        self.assert_cli_waiting(process, entered)
                        release.set()
                        self.assertEqual(first.result(timeout=5)["sessions"][0]["summary"]["status"], "stale")
                        stdout, stderr = process.communicate(timeout=5)
                        self.assertEqual(process.returncode, 0, stdout + stderr)
                source_key = initial["revision"]["source_key"]
                state = collector.store.read()
                logical = copy.deepcopy(state["logical_observations"][source_key])
                logical_size = len(gzip.decompress(t3)) if compressed else len(t3)
                for layer in dashboard.HISTORY_LAYERS:
                    self.assertEqual(state[layer][source_key]["logical"]["size"], logical_size)
                self.assertFalse(state["invalid_snapshots"])
                observer = self.collector(config)
                if compressed:
                    with path.open("ab") as stream:
                        stream.write(b"incomplete gzip tail")
                    observer.collect()
                    state = observer.store.read()
                    self.assertFalse(state["invalid_snapshots"])
                    self.assertEqual(state["logical_observations"][source_key], logical)
                else:
                    observer.collect()
                metrics = dict(observer.adapter.metrics)
                observer.collect()
                self.assertEqual(observer.adapter.metrics, metrics)
                path.write_bytes(t2)
                self.assertEqual(self.collector(config).collect()["sessions"][0]["summary"]["status"], "invalid")
                path.write_bytes(t3)
                self.assertEqual(self.collector(config).collect()["sessions"][0]["summary"]["status"], "invalid")
                state = observer.store.read()
                self.assertEqual(set(state["invalid_snapshots"]), {accepted["snapshot_id"], pending["snapshot_id"]})
                payload = self.root / ("checkpoint-pending-" + str(compressed) + ".json")
                payload.write_text(json.dumps(self.payload(pending)))
                with self.competing_cli(config, "summary-import", "--input", str(payload)) as (process, entered):
                    stdout, stderr = process.communicate(timeout=5)
                    self.assertEqual(process.returncode, 2, stdout + stderr)
                    self.assertIn("무효", stderr)


    def test_incomplete_gzip_tail_does_not_erase_the_logical_comparison_baseline(self):
        path = self.write([message("user", "T1 request")], compressed=True)
        t1 = path.read_bytes()
        issuer = self.collector()
        initial = issuer.collect()["sessions"][0]
        accepted, pending = issuer.store.issue_many([initial, initial])
        issuer.store.accept(self.payload(accepted), {SID: initial})
        with path.open("ab") as stream:
            stream.write(gzip.compress(self.append_data(path, [message("assistant", "T2 progress")]), mtime=1))
        t2 = self.collector().collect()["sessions"][0]
        self.assertEqual(t2["summary"]["status"], "stale")
        path.write_bytes(gzip.compress(gzip.decompress(path.read_bytes()), compresslevel=1, mtime=2))
        self.assertEqual(self.collector().collect()["sessions"][0]["summary"]["status"], "stale")
        with path.open("ab") as stream:
            stream.write(b"incomplete gzip tail")
        observer = self.collector()
        observer.collect()
        state = observer.store.read()
        source_key = initial["revision"]["source_key"]
        self.assertFalse(state["invalid_snapshots"])
        self.assertEqual(state["observations"][source_key]["logical"]["size"], t2["revision"]["size"])
        self.assertEqual(state["latest_observations"][source_key]["failure"], "decode")
        path.write_bytes(t1)
        restored = self.collector()
        self.assertEqual(restored.collect()["sessions"][0]["summary"]["status"], "invalid")
        self.assertIn(pending["snapshot_id"], restored.store.read()["invalid_snapshots"])


    def test_compact_history_budget_excludes_user_text_and_covers_all_layers(self):
        maximal = dashboard.compact_observation({
            "observed_ns": 2**63 - 1,
            "file_stat": [2**64 - 1, 2**64 - 1, 2**63 - 1, -(2**63), 2**63 - 1],
            "failure": "decode", "missing": False, "session_id": "😀" * 200,
            "raw": {"size": 128 * 1024 * 1024, "digest": "a" * 64},
            "logical": {"size": 128 * 1024 * 1024, "digest": "b" * 64, "lineage": "c" * 64},
        })
        self.assertNotIn("session_id", maximal)
        encoded_record = json.dumps(maximal, ensure_ascii=False, separators=(",", ":")).encode()
        self.assertTrue(encoded_record.isascii())
        self.assertLessEqual(len(encoded_record), dashboard.MAX_OBSERVATION_BYTES)
        budget = {layer: {f"{number:064x}": maximal for number in range(dashboard.MAX_SNAPSHOTS)}
                  for layer in dashboard.HISTORY_LAYERS}
        budget["invalid_snapshots"] = {f"{number:032x}": "2000-01-01T00:00:00.000000+00:00"
                                       for number in range(dashboard.MAX_SNAPSHOTS)}
        self.assertLessEqual(len(json.dumps(budget, ensure_ascii=False, separators=(",", ":")).encode()),
                             dashboard.CONTINUITY_RESERVE)


    def test_512_distinct_utf8_sources_preserve_invalidations_at_capacity_and_restore(self):
        ids = [f"11111111-1111-4111-8111-{number:012d}" for number in range(dashboard.MAX_SNAPSHOTS)]
        paths = [self.write([message("user", "reserve request")], sid=sid) for sid in ids]
        originals = [path.read_bytes() for path in paths]
        for mode, replacement_id in (("reserved", "😀" * 200), ("priority", "가" * 200)):
            with self.subTest(mode=mode):
                config = self.configuration("--runtime-dir", str(self.root / ("runtime-" + mode)))
                issuer = self.collector(dict(config, sessions=ids))
                cards = issuer.collect()["sessions"]
                self.assertEqual(len(cards), dashboard.MAX_SNAPSHOTS)
                snapshots = issuer.store.issue_many(cards)
                issuer.store.accept(self.payload(snapshots[0]), {card["id"]: card for card in cards})
                before = issuer.store.path.read_bytes()
                for path in paths:
                    path.write_bytes(encoded(chain([
                        record("system", uuid="new-" + replacement_id, parentUuid=None, cwd=str(self.project)),
                        message("user", "changed request" + ("x" * 2000 if mode == "priority" else ""))], None)))
                if mode == "reserved":
                    boundary = len(before) + dashboard.CONTINUITY_RESERVE
                else:
                    minimal = json.loads(before)
                    minimal["invalid_snapshots"] = {snapshot["snapshot_id"]: "2000-01-01T00:00:00.000000+00:00"
                                                    for snapshot in snapshots}
                    boundary = len(json.dumps(minimal, ensure_ascii=False, separators=(",", ":")).encode()) + 1
                observer = self.collector(config)
                with patch.object(dashboard, "MAX_JSON", boundary):
                    if mode == "reserved":
                        observer.collect()
                    else:
                        with self.assertRaisesRegex(dashboard.DashboardError, "무효화 이력은 저장"):
                            observer.collect()
                    state = observer.store.read()
                    self.assertEqual(len(state["invalid_snapshots"]), dashboard.MAX_SNAPSHOTS)
                    self.assertLessEqual(len(observer.store.path.read_bytes()), boundary)
                    self.assertEqual(state["snapshots"][snapshots[0]["snapshot_id"]], snapshots[0])
                    for layer in dashboard.HISTORY_LAYERS:
                        for proof in state[layer].values():
                            self.assertNotIn("session_id", proof)
                            self.assertLessEqual(len(json.dumps(proof, ensure_ascii=False, separators=(",", ":")).encode()),
                                                 dashboard.MAX_OBSERVATION_BYTES)
                for path, original in zip(paths, originals):
                    path.write_bytes(original)
                restored = self.collector(dict(config, sessions=ids))
                by_id = {card["id"]: card for card in restored.collect()["sessions"]}
                self.assertEqual(by_id[snapshots[0]["session_id"]]["summary"]["status"], "invalid")
                with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
                    restored.store.accept(self.payload(snapshots[-1]), by_id)


    def test_serialized_reads_preserve_real_shrink_and_decode_proofs_before_cli_restore(self):
        modes = ("plain_shrink", "gzip_shrink", "same_size", "larger", "tail", "recompressed_tail", "missing_prefix")
        for mode in modes:
            with self.subTest(mode=mode):
                self.home = self.root / ("serialized-home-" + mode)
                self.home.mkdir()
                config = self.configuration("--runtime-dir", str(self.root / ("runtime-serialized-" + mode)))
                path = self.write([message("user", "ORIGINAL request")], compressed=mode != "plain_shrink")
                original = path.read_bytes()
                collector = self.collector(config)
                initial = collector.collect()["sessions"][0]
                accepted, pending = collector.store.issue_many([initial, initial])
                collector.store.accept(self.payload(accepted), {SID: initial})
                if mode == "recompressed_tail":
                    path.write_bytes(gzip.compress(gzip.decompress(original), compresslevel=1, mtime=1))
                    self.assertEqual(self.collector(config).collect()["sessions"][0]["summary"]["status"], "fresh")
                    restored = gzip.compress(gzip.decompress(original), compresslevel=9, mtime=2)
                else:
                    restored = original
                if mode.endswith("shrink"):
                    data = self.append_data(path, [message("assistant", "T2 progress")])
                    with path.open("ab") as stream:
                        stream.write(gzip.compress(data, mtime=1) if mode == "gzip_shrink" else data)
                elif mode in {"tail", "recompressed_tail"}:
                    with path.open("ab") as stream:
                        stream.write(b"incomplete tail RAW_PRIVATE_SYNTHETIC_SENTINEL")
                else:
                    path.write_bytes(b"BAD" + original[3:] + (b"extra" if mode != "same_size" else b""))
                invalid = mode in {"plain_shrink", "gzip_shrink", "same_size", "larger"}
                payload = self.root / ("serialized-pending-" + mode + ".json")
                payload.write_text(json.dumps(self.payload(pending)))
                with self.held_collection(collector, checkpoints=mode != "missing_prefix") as (first, release):
                    # The writer may restore while a reader holds captured bytes;
                    # the CLI must wait until that observation has been stored.
                    path.write_bytes(restored)
                    with self.competing_cli(config, "summary-import", "--input", str(payload)) as (process, entered):
                        self.assert_cli_waiting(process, entered)
                        release.set()
                        older_card = first.result(timeout=5)["sessions"][0]
                        stdout, stderr = process.communicate(timeout=5)
                        self.assertEqual(process.returncode, 2 if invalid else 0, stdout + stderr)
                        if invalid:
                            self.assertIn("무효", stderr)
                        else:
                            self.assertEqual(json.loads(stdout)["status"], "fresh")
                self.assertEqual(collector.adapter.metrics["read_calls"], 2)
                self.assertEqual(collector.adapter.metrics["parse_calls"], 2 if mode.endswith("shrink") else 1)
                state = collector.store.read()
                self.assertEqual(len(state["invalid_snapshots"]), 2 if invalid else 0)
                self.assertEqual(state["snapshots"][accepted["snapshot_id"]]["evidence"], accepted["evidence"])
                self.assertEqual(state["snapshots"][pending["snapshot_id"]]["evidence"], pending["evidence"])
                # Replaying an older cached record cannot overwrite newer CLI facts.
                old = copy.deepcopy(collector.cache[path][1]["_observation"])
                collector.store.observe([{**old, "source_key": initial["revision"]["source_key"],
                                          "path": str(path), "session_id": SID}])
                for layer in dashboard.HISTORY_LAYERS:
                    self.assertEqual(collector.store.read()[layer], state[layer])
                if mode.endswith("shrink"):
                    with self.assertRaisesRegex(dashboard.DashboardError, "다시 수집"):
                        collector.store.issue(older_card)
                fresh = self.collector(config)
                current = fresh.collect()["sessions"][0]
                self.assertEqual(current["summary"]["status"], "invalid" if invalid else "fresh")
                self.assertEqual(path.read_bytes(), restored)
                metrics = dict(fresh.adapter.metrics)
                fresh.collect()
                self.assertEqual(fresh.adapter.metrics, metrics)
                public = json.dumps(state) + json.dumps(current)
                self.assertNotIn("_raw_baseline", public)
                self.assertNotIn("RAW_PRIVATE_SYNTHETIC_SENTINEL", public)


    def test_collection_locks_are_runtime_scoped_for_threads_and_processes(self):
        self.write([message("user", "independent runtime request")])
        first, second = self.collector(), self.collector()
        attempted, read_entered = threading.Event(), threading.Event()
        original_read = second.adapter.read

        def read(*args, **kwargs):
            read_entered.set()
            return original_read(*args, **kwargs)

        def compete():
            attempted.set()
            return second.collect()

        separate = self.configuration("--runtime-dir", str(self.root / "independent-runtime"))
        with patch.object(second.adapter, "read", side_effect=read):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                with self.held_collection(first, before_read=True) as (holding, release):
                    waiting = pool.submit(compete)
                    self.assertTrue(attempted.wait(5))
                    self.assertFalse(read_entered.wait(0.2), "same-runtime thread entered before release")
                    with self.competing_cli(separate, "summary-input") as (process, entered):
                        stdout, stderr = process.communicate(timeout=5)
                        self.assertEqual(process.returncode, 0, stdout + stderr)
                        self.assertTrue(entered.exists())
                    self.assertFalse(read_entered.is_set())
                    release.set()
                    self.assertEqual(holding.result(timeout=5)["sessions"][0]["id"], SID)
                    self.assertEqual(waiting.result(timeout=5)["sessions"][0]["id"], SID)
        self.assertTrue(read_entered.is_set())


    def test_collection_lock_releases_after_read_and_observation_errors(self):
        self.write([message("user", "error release request")])
        for stage in ("read", "observe"):
            with self.subTest(stage=stage):
                collector = self.collector()
                target = collector.adapter if stage == "read" else collector.store
                with patch.object(target, stage, side_effect=RuntimeError("synthetic collection failure")):
                    with self.assertRaisesRegex(RuntimeError, "synthetic collection failure"):
                        collector.collect()
                with self.competing_cli(self.config, "summary-input") as (process, entered):
                    stdout, stderr = process.communicate(timeout=5)
                    self.assertEqual(process.returncode, 0, stdout + stderr)
                    self.assertTrue(entered.exists())
                self.assertEqual(collector.collect()["sessions"][0]["id"], SID)


    def test_unverified_expansion_limit_and_permissions_preserve_last_good_proof(self):
        path = self.write([message("user", "small request")], compressed=True)
        original = path.read_bytes()
        config = self.configuration("--max-bytes", "2048", "--session", SID)
        issuer = self.collector(config)
        card = issuer.collect()["sessions"][0]
        snapshot = issuer.store.issue(card)
        issuer.store.accept(self.payload(snapshot), {SID: card})
        source_key = card["revision"]["source_key"]
        baseline = copy.deepcopy(issuer.store.read()["observations"][source_key])
        path.write_bytes(gzip.compress(gzip.decompress(original) + b"x" * 100000))
        observer = self.collector(config)
        observer.collect()
        self.assertEqual(observer.adapter.metrics["read_calls"], 1)
        self.assertEqual(observer.adapter.metrics["read_bytes"], path.stat().st_size)
        self.assertEqual(observer.adapter.metrics["expanded_bytes"], 2049)
        self.assertEqual(observer.adapter.metrics["parse_calls"], 0)
        self.assertEqual(observer.store.read()["observations"][source_key], baseline)
        self.assertFalse(observer.store.read()["invalid_snapshots"])
        path.write_bytes(original)
        unavailable = self.collector(config)
        with patch.object(unavailable.adapter, "read", side_effect=PermissionError("temporary")):
            unavailable.collect()
        self.assertEqual(unavailable.store.read()["observations"][source_key], baseline)
        self.assertFalse(unavailable.store.read()["invalid_snapshots"])
        self.assertEqual(unavailable.collect()["sessions"][0]["summary"]["status"], "fresh")
        self.assertEqual(unavailable.adapter.metrics["parse_calls"], 1)


    def test_late_snapshot_checkpoint_is_unknown_not_a_proven_rewrite(self):
        path = self.write([message("user", "initial request")])
        collector = self.collector()
        captured = collector.collect()["sessions"][0]
        self.append(path, [message("assistant", "ordinary append")])
        collector.collect()
        metrics = dict(collector.adapter.metrics)
        # Simulate another process issuing its previously collected input after this read.
        snapshot = collector.store.issue(captured)
        collector.collect()
        self.assertNotIn(snapshot["snapshot_id"], collector.store.read()["invalid_snapshots"])
        importer = self.collector()
        current = importer.collect()["sessions"][0]
        self.assertEqual(importer.store.accept(self.payload(snapshot), {SID: current})["status"], "stale")
        cached_view = collector.collect()["sessions"][0]
        self.assertEqual(cached_view["summary"]["status"], "stale")
        self.assertEqual(collector.adapter.metrics, metrics)
        self.assertNotIn("validated_revision", cached_view["summary"])


    def test_atomic_batches_preserve_65_and_200_inputs_and_capacity_failures(self):
        for count in (65, 200):
            with self.subTest(count=count):
                for number in range(count):
                    self.write([message("user", "합성 요청")], sid=f"11111111-1111-4111-8111-{number:012d}")
                collector = self.collector(self.configuration("--limit", str(count)))
                cards = collector.collect()["sessions"]
                self.assertEqual(len(cards), count)
                by_id = {card["id"]: card for card in cards}
                snapshots = collector.store.issue_many(cards)
                self.assertEqual(len(snapshots), count)
                state = collector.store.read()
                self.assertTrue(all(snapshot["snapshot_id"] in state["snapshots"] for snapshot in snapshots))
                self.assertEqual([snapshot["sequence"] for snapshot in snapshots], list(range(snapshots[0]["sequence"], snapshots[0]["sequence"] + count)))
                for snapshot in (snapshots[0], snapshots[-1]):
                    self.assertEqual(collector.store.accept(self.payload(snapshot), by_id)["status"], "fresh")
        for snapshot in snapshots[1:-1]:
            collector.store.accept(self.payload(snapshot), by_id)
        self.assertEqual(len(collector.store.read()["summaries"]), 200)
        refreshed = collector.store.issue_many(cards)
        self.assertEqual(len(refreshed), 200)
        self.assertEqual(len(collector.store.read()["snapshots"]), 400)
        for snapshot in refreshed:
            collector.store.accept(self.payload(snapshot), by_id)
        compacted = collector.store.issue(cards[0])
        before = collector.store.path.read_bytes()
        with self.assertRaisesRegex(dashboard.DashboardError, "스냅샷이 너무 많습니다"):
            collector.store.issue_many(cards + cards)
        self.assertEqual(collector.store.path.read_bytes(), before)
        with patch.object(dashboard, "MAX_JSON", len(before) + 1):
            with self.assertRaisesRegex(dashboard.DashboardError, "허용 크기"):
                collector.store.issue_many(cards)
        self.assertEqual(collector.store.path.read_bytes(), before)
        self.assertEqual(collector.store.accept(self.payload(compacted), by_id)["status"], "fresh")
        self.assertEqual(collector.store.read()["snapshots"][refreshed[0]["snapshot_id"]], refreshed[0])


    def test_cli_summary_input_issues_one_preserved_batch(self):
        for number in range(65):
            self.write([message("user", "batch goal")], sid=f"11111111-1111-4111-8111-{number:012d}")
        common = [sys.executable, "-I", "-B", str(SCRIPT), "--home", str(self.home),
                  "--project", str(self.project), "--runtime-dir", str(self.runtime),
                  "--self", "observer", "--limit", "65"]
        result = subprocess.run([*common, "summary-input"], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshots = json.loads(result.stdout)["inputs"]
        self.assertEqual(len(snapshots), 65)
        for index in (0, -1):
            payload = self.root / f"batch-summary-{index}.json"
            payload.write_text(json.dumps(self.payload(snapshots[index])))
            result = subprocess.run([*common, "summary-import", "--input", str(payload)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "fresh")


    def test_scope_self_missing_cwd_prefix_and_explicit_override(self):
        self.write([message("user", "first")])
        sibling = self.project.with_name("project-other")
        sibling.mkdir()
        self.write([message("user", "other")], OTHER, cwd=sibling)
        self.write([message("user", "unknown")], THIRD, cwd=None)
        self.assertEqual([card["id"] for card in self.collector().collect()["sessions"]], [SID])
        self.assertEqual(self.collector(self.configuration("--self", SID)).collect()["sessions"], [])
        cards = self.collector(self.configuration("--self", SID, "--include-self")).collect()["sessions"]
        self.assertEqual(cards[0]["id"], SID)
        config = self.configuration("--session", OTHER, "--since-hours", "0.01")
        self.assertEqual(self.collector(config).collect()["sessions"][0]["id"], OTHER)
        with self.assertRaisesRegex(dashboard.DashboardError, "후보:.*11111111"):
            self.collector(self.configuration("--session", "11111111")).collect()
        self.assertEqual(self.collector(self.configuration("--session", THIRD[:8])).collect()["sessions"][0]["id"], THIRD)

    def test_self_id_normalization_precedes_configuration_hash(self):
        unknown = self.configuration("--self", "")
        for value in (" ", "\t\n", "$CODEX_THREAD_ID", "${CODEX_THREAD_ID}",
                      "$CLAUDE_SESSION_ID", "${CLAUDE_SESSION_ID}", " ${OTHER_SESSION_ID} ",
                      "${OTHER_SESSION_ID:-fallback}"):
            with self.subTest(value=value):
                config = self.configuration("--self", value)
                self.assertIsNone(config["self_id"])
                self.assertEqual(config["config_id"], unknown["config_id"])
        exact = self.configuration("--self", SID)
        padded = self.configuration("--self", " \t" + SID + "\n")
        self.assertEqual(padded["self_id"], SID)
        self.assertEqual(padded["config_id"], exact["config_id"])
        with patch.object(source, "defaults", return_value={"home": str(self.home), "self_id": None}):
            args = dashboard.parser(source).parse_args([
                "--home", str(self.home), "--project", str(self.project),
                "--runtime-dir", str(self.runtime), "summary-input"])
            missing = dashboard.configuration(args, source)
        self.assertEqual(missing["config_id"], unknown["config_id"])

    def test_cli_and_environment_self_ids_report_exclusion_honestly(self):
        self.write([message("user", "observer session")])
        self.write([message("user", "another session")], OTHER)
        values = (None, "", " \t\n", "$CODEX_THREAD_ID", "${CODEX_THREAD_ID}",
                  "$CLAUDE_SESSION_ID", "${CLAUDE_SESSION_ID}", SID, " \t" + SID + "\n")
        case = 0
        for mode in ("cli", "environment"):
            for value in values:
                with self.subTest(mode=mode, value=value):
                    case += 1
                    output = self.root / f"self-case-{case}.html"
                    command = [sys.executable, "-I", "-B", str(SCRIPT), "--home", str(self.home),
                               "--project", str(self.project), "--runtime-dir", str(self.runtime)]
                    environment = {"PATH": os.defpath, "HOME": str(self.root)}
                    if value is not None:
                        if mode == "cli":
                            # An explicit unknown ID must override even a valid environment default.
                            environment["CLAUDE_SESSION_ID"] = SID
                            command.extend(["--self", value])
                        else:
                            environment["CLAUDE_SESSION_ID"] = value
                    result = subprocess.run([*command, "export", "--output", str(output)],
                                            capture_output=True, text=True, env=environment, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    document = output.read_text()
                    data = document.split('<script id="dashboard-data" type="application/json">', 1)[1].split("</script>", 1)[0]
                    view = json.loads(data)
                    valid = mode == "cli" and value is not None and value.strip() == SID
                    self.assertEqual(view["selection"]["self_exclusion"], "confirmed" if valid else "unconfirmed")
                    self.assertEqual({card["id"] for card in view["sessions"]}, {OTHER} if valid else {SID, OTHER})
                    warnings = [warning for warning in view["warnings"] if "자기 세션 제외 여부" in warning]
                    self.assertEqual(bool(warnings), not valid)

    def test_default_root_git_worktree_and_separate_nested_worktree(self):
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        subprocess.run(["git", "-C", str(self.project), "-c", "user.name=Fixture", "-c", "user.email=fixture@example.test",
                        "commit", "--allow-empty", "-qm", "Fixture"], check=True)
        nested = self.project / "other-worktree"
        subprocess.run(["git", "-C", str(self.project), "worktree", "add", "-qb", "other", str(nested)], check=True)
        child = self.project / "child"
        child.mkdir()
        self.assertEqual(dashboard.project_root(child), self.project)
        self.assertEqual(dashboard.project_root(nested), nested)
        self.assertTrue(dashboard.within(str(child), str(self.project)))
        self.assertFalse(dashboard.within(str(nested), str(self.project)))
        self.write([message("user", "main")])
        self.write([message("user", "separate")], OTHER, cwd=nested)
        self.assertEqual([c["id"] for c in self.collector().collect()["sessions"]], [SID])
        cards = self.collector(self.configuration("--project", str(nested))).collect()["sessions"]
        self.assertEqual({c["id"] for c in cards}, {SID, OTHER})

    def test_identity_rename_duplicate_titles_and_subagent(self):
        path = self.write([message("user", "자동 제목이 되는 실제 요청입니다.")])
        self.write([message("user", "other")], OTHER)
        self.write([message("user", "child", isSidechain=True)], THIRD)
        collector = self.collector()
        first = {c["id"]: c for c in collector.collect()["sessions"]}
        self.assertEqual(first[SID]["title_source"], "automatic")
        self.assertNotIn(THIRD, first)
        self.registry(SID, name="동일한 제목")
        self.registry(OTHER, name="동일한 제목")
        second = collector.collect(True)["sessions"]
        self.assertEqual({c["id"] for c in second}, {SID, OTHER})
        self.assertEqual({c["title"] for c in second}, {"동일한 제목"})
        self.registry(SID, name="바뀐 제목")
        third = {c["id"]: c for c in collector.collect(True)["sessions"]}
        self.assertEqual(third[SID]["title"], "바뀐 제목")
        self.assertEqual(collector.adapter.metrics["parse_calls"], 3)
        for title in ("A", "B", "A"):
            self.append(path, [record("custom-title", customTitle=title)])
            self.assertEqual(next(c for c in collector.collect()["sessions"] if c["id"] == SID)["title"], title)
        self.append(path, [record("custom-title", customTitle="")])
        self.assertEqual(next(c for c in collector.collect()["sessions"] if c["id"] == SID)["title"], "바뀐 제목")

    def test_project_scope_uses_session_start_cwd_after_directory_changes(self):
        elsewhere = self.root / "elsewhere"
        elsewhere.mkdir()
        self.write([message("user", "started here"), message("assistant", "moved away", cwd=str(elsewhere))])
        self.write([message("user", "started elsewhere"), message("assistant", "moved in", cwd=str(self.project))],
                   OTHER, cwd=elsewhere)
        cards = self.collector().collect()["sessions"]
        self.assertEqual([card["id"] for card in cards], [SID])
        self.assertEqual(cards[0]["cwd"], str(self.project))

    def test_recorded_turn_skips_trailing_local_command_and_meta_records(self):
        reply = message("assistant", "Recorded response")
        reply["message"]["stop_reason"] = "end_turn"
        caveat = message("user", "Caveat: local commands follow", isMeta=True)
        command = record("user", message={"role": "user", "content": "<command-name>/exit</command-name>"})
        output = record("user", message={"role": "user", "content": "<local-command-stdout>Bye!</local-command-stdout>"})
        summary = message("user", "This session is being continued", isCompactSummary=True)
        self.write([message("user", "Finish goal"), reply, summary, caveat, command, output])
        self.assertIn("턴 종료", self.collector().collect()["sessions"][0]["recorded_turn"])
        self.write([message("user", "Finish goal"), reply, message("user", "Follow-up request")], OTHER)
        cards = {card["id"]: card for card in self.collector().collect()["sessions"]}
        self.assertEqual(cards[OTHER]["recorded_turn"], "불명")

    def test_state_honesty_and_unknown_self(self):
        reply = message("assistant", "Recorded response")
        reply["message"]["stop_reason"] = "end_turn"
        self.write([message("user", "Finish goal"), reply])
        self.registry(name="Named session", status="busy", pid=os.getpid())
        config = dict(self.config, self_id=None)
        view = self.collector(config).collect()
        card = view["sessions"][0]
        self.assertEqual(card["live"]["state"], "unknown")
        self.assertIn("busy", card["live"]["provenance"])
        self.assertIn("미확인", card["live"]["provenance"])
        self.assertIsNotNone(card["live"]["observed_at"])
        self.assertIn("턴 종료", card["recorded_turn"])
        self.assertNotIn("goal_complete", card)
        self.assertIsNone(card["summary_at"])
        self.assertIsNotNone(card["last_activity"])
        self.assertIsNotNone(card["collected_at"])
        self.assertEqual(view["selection"]["self_exclusion"], "unconfirmed")

    def test_summary_roundtrip_validation_order_and_captured_refs(self):
        path = self.write([message("user", "ORIGINAL request")])
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        snapshot = collector.store.issue(card)
        old_id = snapshot["evidence"][0]["id"]
        self.append(path, [message("assistant", "RECORDED PROGRESS")])
        card = collector.collect()["sessions"][0]
        self.assertEqual(card["evidence"][0]["id"], old_id)
        accepted = collector.store.accept(self.payload(snapshot), {SID: card})
        self.assertEqual(accepted["status"], "stale")
        self.assertEqual(accepted["evidence"][0]["text"], "ORIGINAL request")
        self.assertEqual(accepted["evidence"][0]["id"], old_id)
        self.assertEqual(accepted["fields"]["remaining"], [])
        newer = collector.store.issue(card)
        with self.assertRaisesRegex(dashboard.DashboardError, "refs"):
            collector.store.accept(self.payload(newer, ref="99999"), {SID: card})
        wrong = dict(self.payload(newer), session_id=OTHER)
        with self.assertRaises(dashboard.DashboardError):
            collector.store.accept(wrong, {SID: card})
        collector.store.accept(self.payload(newer), {SID: card})
        with self.assertRaisesRegex(dashboard.DashboardError, "더 최근"):
            collector.store.accept(self.payload(snapshot), {SID: card})
        state = collector.store.read()
        self.assertEqual(state["snapshots"][snapshot["snapshot_id"]], snapshot)

    def test_summary_rewind_replacement_truncation_and_branch_invalidation(self):
        changes = ["rewind", "replace", "truncate", "branch"]
        for change in changes:
            with self.subTest(change=change):
                path = self.write([message("user", "goal"), message("assistant", "abandoned response")])
                collector = self.collector()
                card = collector.collect()["sessions"][0]
                snapshot = collector.store.issue(card)
                collector.store.accept(self.payload(snapshot), {SID: card})
                if change == "rewind":
                    self.append(path, [message("user", "new goal", parentUuid="root-" + SID)])
                elif change == "branch":
                    self.append(path, [message("assistant", "revised response", parentUuid=json.loads(path.read_text().splitlines()[1])["uuid"])])
                elif change == "replace":
                    new = path.with_suffix(".replacement")
                    new.write_bytes(path.read_bytes())
                    os.replace(new, path)
                else:
                    path.write_bytes(encoded([record("system", uuid="root-" + SID, parentUuid=None, cwd=str(self.project))]))
                card = collector.collect()["sessions"][0]
                self.assertEqual(card["summary"]["status"], "invalid")
                with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
                    collector.store.accept(self.payload(snapshot), {SID: card})

    def test_observed_truncation_cannot_resurrect_a_snapshot(self):
        path = self.write([message("user", "goal"), message("assistant", "progress")])
        original = path.read_bytes()
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        snapshot = collector.store.issue(card)
        collector.store.accept(self.payload(snapshot), {SID: card})
        path.write_bytes(original[:original.index(b"\n") + 1])
        self.assertEqual(collector.collect()["sessions"][0]["summary"]["status"], "invalid")
        path.write_bytes(original)
        self.assertEqual(collector.collect()["sessions"][0]["summary"]["status"], "invalid")

    def test_recent_limit_and_unscoped_failure_warnings(self):
        self.write([message("user", "one")])
        self.write([message("user", "two")], OTHER)
        old = self.write([message("user", "old")], THIRD)
        rows = [record("user", uuid="old", parentUuid=None, cwd=str(self.project), message={"content": "old"})]
        for row in rows:
            row["timestamp"] = "2000-01-01T00:00:00Z"
        old.write_bytes(encoded(rows))
        view = self.collector(self.configuration("--limit", "1")).collect()
        self.assertEqual(len(view["sessions"]), 1)
        self.assertEqual(view["omitted_sessions"], 1)
        self.assertTrue(view["warnings"])
        old.write_bytes(b"x" * 3000)
        view = self.collector(self.configuration("--max-bytes", "2048")).collect()
        self.assertTrue(any("읽지 못했습니다" in warning for warning in view["warnings"]))

    def test_summary_sanitization_and_unknown_fields(self):
        self.write([message("user", "goal")])
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        snapshot = collector.store.issue(card)
        payload = self.payload(snapshot, "api_key=topsecret <file>attached secret</file> 해결합니다.")
        accepted = collector.store.accept(payload, {SID: card})
        text = accepted["fields"]["goal"][0]["text"]
        self.assertNotIn("topsecret", text)
        self.assertNotIn("attached secret", text)
        newer = collector.store.issue(card)
        payload = self.payload(newer)
        payload["fields"]["unexpected"] = []
        with self.assertRaises(dashboard.DashboardError):
            collector.store.accept(payload, {SID: card})

    def test_unchanged_read_parse_metadata_counts_and_truncation_anchors(self):
        rows = [message("user", "FIRST GOAL")]
        rows.extend(message("assistant", "x" * 2400) for _ in range(120))
        rows += [record("system", subtype="compact_boundary"), message("user", "LATEST REQUEST")]
        path = self.write(rows)
        self.registry(name="Title", status="idle")
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        metrics = dict(collector.adapter.metrics)
        for _ in range(3):
            collector.collect(True)
        self.assertEqual(collector.adapter.metrics, metrics)
        self.assertEqual(metrics["metadata_reads"], 1)
        self.assertEqual(metrics["registry_reads"], 1)
        self.assertEqual(len(card["events"]), 40)
        self.assertEqual(len(card["evidence"]), 100)
        texts = [e["text"] for e in card["evidence"]]
        self.assertIn("FIRST GOAL", texts)
        self.assertIn("LATEST REQUEST", texts)
        self.assertIn("기록이 압축되었습니다.", texts)
        self.assertTrue(all(len(text) <= 2000 for text in texts))
        self.assertEqual(card["truncation"]["recent_events"], 83)
        self.assertEqual(card["truncation"]["text_characters"], 120 * 400)
        self.append(path, [message("assistant", "new")])
        collector.collect()
        self.assertEqual(collector.adapter.metrics["parse_calls"], 2)

    def test_metadata_hook_refreshes_cached_live_state_without_touching_evidence(self):
        path = self.write([message("user", "original goal")])
        collector = self.collector()
        registry = {"live": {"state": "unknown", "provenance": {
            "source": "fixture registry", "reported_status": "busy", "confirmed": False},
            "observed_at": "2026-11-12T00:00:00+00:00"}, "warnings": ["등록 상태는 현재 실행의 증거가 아닙니다."]}
        calls = []

        def refresh(card):
            calls.append(card["id"])
            # An adapter may attach its cached nested objects directly.
            card["live"] = registry["live"]
            card["warnings"] = registry["warnings"]
            # Changes outside the small metadata contract must never escape.
            card["revision"]["digest"] = "changed digest"
            card["evidence"][0]["text"] = "changed evidence"
            card["events"][0]["text"] = "changed event"
            card["id"] = "changed id"
            card["subagent"] = True
            card["scope_cwd"] = None
            card["automatic_title"] = "changed title"

        with patch.object(collector.adapter, "refresh_metadata", refresh, create=True):
            first = collector.collect()
            frozen_first = copy.deepcopy(first)
            metrics = dict(collector.adapter.metrics)
            cached = copy.deepcopy(collector.cache[path][1])
            self.assertEqual(metrics["parse_calls"], 1)
            self.assertEqual(metrics["metadata_reads"], 1)
            self.assertEqual(first["sessions"][0]["id"], SID)
            self.assertEqual(first["sessions"][0]["title"], "original goal")
            self.assertEqual(first["sessions"][0]["revision"], cached["revision"])
            self.assertEqual(first["sessions"][0]["evidence"], cached["evidence"])
            self.assertEqual(first["sessions"][0]["events"], cached["events"])
            registry["live"]["provenance"]["reported_status"] = "idle"
            registry["live"]["observed_at"] = "2026-11-12T00:01:00+00:00"
            registry["warnings"].append("등록 메타데이터가 갱신되었습니다.")
            second = collector.collect()
            self.assertEqual(calls, [SID, SID])
            self.assertEqual(collector.adapter.metrics, metrics)
            self.assertEqual(collector.cache[path][1], cached)
            self.assertEqual(first, frozen_first)
            self.assertEqual(second["sessions"][0]["live"]["provenance"]["reported_status"], "idle")
            self.assertEqual(second["sessions"][0]["live"]["observed_at"], "2026-11-12T00:01:00+00:00")
            self.assertEqual(second["sessions"][0]["revision"], first["sessions"][0]["revision"])
            self.assertEqual(second["sessions"][0]["evidence"], first["sessions"][0]["evidence"])

    def test_metadata_hook_failure_is_local_and_recovers_without_reparsing(self):
        self.write([message("user", "first goal")])
        self.write([message("user", "second goal")], OTHER)
        collector = self.collector()
        failing = True

        def refresh(card):
            if card["id"] == SID and failing:
                card["live"]["state"] = "running"
                card["evidence"][0]["text"] = "corrupted"
                raise source.SourceError("api_key=private-registry-detail")
            card["live"]["provenance"] = "fixture registry"

        with patch.object(collector.adapter, "refresh_metadata", refresh, create=True):
            first = collector.collect()
            cards = {card["id"]: card for card in first["sessions"]}
            metrics = dict(collector.adapter.metrics)
            self.assertEqual(cards[SID]["live"]["state"], "unknown")
            self.assertEqual(cards[SID]["evidence"][0]["text"], "first goal")
            self.assertIsNotNone(cards[SID]["revision"])
            self.assertTrue(any("메타데이터를 갱신하지 못했습니다" in warning for warning in cards[SID]["warnings"]))
            self.assertFalse(cards[OTHER]["warnings"])
            self.assertEqual(cards[OTHER]["live"]["provenance"], "fixture registry")
            self.assertNotIn("private-registry-detail", json.dumps(first))
            failing = False
            second = {card["id"]: card for card in collector.collect()["sessions"]}
            self.assertFalse(second[SID]["warnings"])
            self.assertEqual(second[SID]["live"]["provenance"], "fixture registry")
            self.assertEqual(collector.adapter.metrics, metrics)

    def test_actual_expansion_bound_precedes_any_parser_or_metadata(self):
        path = self.write([message("user", "x" * 100000)], compressed=True)
        config = self.configuration("--max-bytes", "2048", "--session", SID)
        self.assertLess(path.stat().st_size, 2048)
        collector = self.collector(config)
        card = collector.collect()["sessions"][0]
        self.assertIn("바이트 상한", card["warnings"][0])
        self.assertEqual(collector.adapter.metrics["expanded_bytes"], 2049)
        self.assertEqual(collector.adapter.metrics["parse_calls"], 0)
        self.assertEqual(collector.adapter.metrics["metadata_reads"], 0)
        metrics = dict(collector.adapter.metrics)
        collector.collect()
        self.assertEqual(collector.adapter.metrics, metrics)
        plain = self.write([message("user", "x" * 3000)], sid=OTHER)
        other = self.collector(self.configuration("--max-bytes", "2048", "--session", OTHER))
        other.collect()
        self.assertGreater(plain.stat().st_size, 2048)
        self.assertEqual(other.adapter.metrics["parse_calls"], 0)

    def test_corrupt_partial_gzip_permissions_and_removed_isolated(self):
        path = self.write([message("user", "good")])
        with path.open("ab") as stream:
            stream.write(b'{"partial":')
        bad = self.write([message("user", "bad")], OTHER, compressed=True)
        bad.write_bytes(b"not-gzip")
        collector = self.collector(self.configuration("--session", SID, "--session", OTHER))
        cards = {card["id"]: card for card in collector.collect()["sessions"]}
        self.assertEqual(cards[SID]["events"][0]["text"], "good")
        self.assertTrue(cards[SID]["warnings"])
        self.assertTrue(cards[OTHER]["warnings"])
        path.unlink()
        cards = {card["id"]: card for card in collector.collect()["sessions"]}
        self.assertIsNone(cards[SID]["revision"])
        with patch.object(source, "signature", side_effect=PermissionError("denied")):
            self.assertTrue(collector.collect()["sessions"][0]["warnings"])

    def test_readonly_hashes_redaction_and_filtered_evidence(self):
        secret = "sk-ant-" + "A" * 30
        tool = record("assistant", message={"content": [
            {"type": "thinking", "thinking": "PRIVATE THOUGHT"},
            {"type": "tool_use", "id": "call", "name": "Edit", "input": {"file_path": "src/file.py", "old_string": "RAW DIFF"}},
            {"type": "tool_use", "id": "bash", "name": "Bash", "input": {"command": "RAW COMMAND"}}]})
        result = record("user", message={"content": [{"type": "tool_result", "tool_use_id": "call", "content": "RAW RESULT"}]})
        self.write([record("user", isMeta=True, message={"content": "INJECTED"}),
                    message("user", "# CLAUDE.md instructions INJECTED"),
                    message("user", "Actual goal " + secret + " <attachment>ATTACHED BODY</attachment>"),
                    record("attachment", attachment={"type": "file", "filename": "PRIVATE ATTACHMENT"}),
                    tool, result])
        self.registry(name="Title api_key=topsecret", status="busy", pid=os.getpid())
        before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in self.home.rglob("*") if p.is_file()}
        collector = self.collector()
        view = collector.collect()
        wire = json.dumps(view)
        for value in (secret, "topsecret", "INJECTED", "ATTACHED BODY", "PRIVATE ATTACHMENT", "PRIVATE THOUGHT", "RAW COMMAND", "RAW RESULT", "RAW DIFF"):
            self.assertNotIn(value, wire)
        self.assertIn("src/file.py", wire)
        self.assertIn("[REDACTED]", wire)
        collector.store.issue(view["sessions"][0])
        self.assertEqual(before, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in before})
        self.assertEqual(set(before), {p for p in self.home.rglob("*") if p.is_file()})

    def test_dependency_errors_runtime_security_and_bounds(self):
        with self.assertRaisesRegex(source.SourceError, "의존성"):
            source.Adapter(self.home, 1024, parser_path=self.root / "absent.py")
        incompatible = self.root / "incompatible.py"
        incompatible.write_text("Catalog = object\n")
        with self.assertRaisesRegex(source.SourceError, "호환"):
            source.Adapter(self.home, 1024, parser_path=incompatible)
        self.assertEqual(self.runtime.stat().st_mode & 0o777, 0o700)
        dashboard.write_json(self.runtime / "private.json", {"x": "y"})
        self.assertEqual((self.runtime / "private.json").stat().st_mode & 0o777, 0o600)
        link = self.root / "link"
        link.symlink_to(self.runtime, target_is_directory=True)
        with self.assertRaises(dashboard.DashboardError):
            dashboard.private_dir(link / "child")
        public = self.root / "public"
        public.mkdir(mode=0o755)
        with self.assertRaises(dashboard.DashboardError):
            dashboard.private_dir(public)
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                self.configuration("--max-bytes", "0")
            with self.assertRaises(SystemExit):
                self.configuration("--since-hours", "nan")

    def test_registry_observation_cache_change_removal_and_errors(self):
        self.write([message("user", "goal")])
        registry = self.registry(name="First", status="busy", pid=os.getpid())
        collector = self.collector()
        first = collector.collect()["sessions"][0]
        original = copy.deepcopy(first)
        metrics = dict(collector.adapter.metrics)
        for _ in range(3):
            same = collector.collect(True)["sessions"][0]
            self.assertEqual(same["live"], first["live"])
        self.assertEqual(collector.adapter.metrics, metrics)
        self.registry(name="Renamed", status="idle", pid=os.getpid())
        # The metadata hook itself reads nothing, even after a registry change.
        before_discovery = collector.collect()["sessions"][0]
        self.assertEqual(before_discovery["live"], first["live"])
        changed = collector.collect(True)["sessions"][0]
        self.assertEqual(changed["title"], "Renamed")
        self.assertEqual(changed["live"]["state"], "unknown")
        self.assertIn("idle", changed["live"]["provenance"])
        self.assertNotEqual(changed["live"]["observed_at"], first["live"]["observed_at"])
        self.assertEqual(collector.adapter.metrics["parse_calls"], 1)
        self.assertEqual(collector.adapter.metrics["registry_reads"], 2)
        self.assertEqual(first, original)
        registry.unlink()
        removed = collector.collect(True)["sessions"][0]
        self.assertEqual(removed["title"], "goal")
        self.assertIn("등록 정보 없음", removed["live"]["provenance"])
        self.assertNotEqual(removed["live"]["observed_at"], changed["live"]["observed_at"])
        self.assertEqual(collector.adapter.metrics["registry_reads"], 2)
        registry.write_text("{broken")
        broken = collector.collect(True)
        self.assertTrue(broken["warnings"])
        self.assertIn("해석 불가", broken["sessions"][0]["live"]["provenance"])
        metrics = dict(collector.adapter.metrics)
        collector.collect(True)
        self.assertEqual(collector.adapter.metrics, metrics)

    def test_rewind_active_evidence_root_rewind_and_logical_parent(self):
        first = message("user", "first goal")
        first_answer = message("assistant", "first answer")
        second = message("user", "abandoned goal")
        path = self.write([first, first_answer, second, message("assistant", "abandoned answer")])
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        snapshot = collector.store.issue(card)
        self.append(path, [message("user", "replacement goal", parentUuid=first_answer["uuid"]),
                           message("assistant", "replacement answer")])
        card = collector.collect()["sessions"][0]
        texts = [event["text"] for event in card["evidence"]]
        self.assertEqual(texts, ["first goal", "first answer", "replacement goal", "replacement answer"])
        with self.assertRaisesRegex(dashboard.DashboardError, "무효"):
            collector.store.accept(self.payload(snapshot), {SID: card})
        fresh = collector.store.issue(card)
        leaf = json.loads(path.read_text().splitlines()[-1])["uuid"]
        self.append(path, [record("system", subtype="compact_boundary", parentUuid=None, logicalParentUuid=leaf),
                           message("assistant", "continued answer")])
        after = collector.collect()["sessions"][0]
        self.assertEqual(collector.store.accept(self.payload(fresh), {SID: after})["status"], "stale")
        reset = message("user", "new root", parentUuid=None, cwd=str(self.project))
        self.append(path, [reset])
        card = collector.collect()["sessions"][0]
        self.assertEqual([event["text"] for event in card["evidence"]], ["new root"])
        self.assertEqual(card["summary"]["status"], "invalid")

    def test_home_override_and_bounded_private_snapshot_parser_reuse(self):
        path = self.write([message("user", "goal")])
        adapter = source.Adapter(self.home, 2048)
        self.assertEqual(adapter.parser.CLAUDE_HOME, self.home)
        snapshots = []
        original_session = adapter.parser.Session

        def parse(snapshot, **kwargs):
            snapshots.append(Path(snapshot))
            self.assertNotEqual(snapshot, path)
            self.assertEqual(snapshot.stat().st_mode & 0o777, 0o600)
            self.assertEqual(snapshot.parent.stat().st_mode & 0o777, 0o700)
            self.assertLessEqual(snapshot.stat().st_size, 2048)
            return original_session(snapshot, **kwargs)

        with patch.object(adapter.parser, "Session", side_effect=parse), \
             patch.object(adapter.parser, "quick_meta", side_effect=AssertionError("unbounded metadata")), \
             patch.object(adapter.parser, "live_index", side_effect=AssertionError("global home")), \
             patch.object(adapter.parser, "all_transcripts", side_effect=AssertionError("global home")):
            adapter.discover()
            card = adapter.read(path)
        self.assertEqual(card["evidence"][0]["text"], "goal")
        self.assertTrue(snapshots)
        self.assertTrue(all(not snapshot.exists() for snapshot in snapshots))
        with patch.dict(os.environ, {"CLAUDE_SESSION_ID": SID, "CLAUDE_CONFIG_DIR": str(self.home)}):
            self.assertEqual(source.defaults(), {"home": str(self.home), "self_id": None})

    def test_registry_size_limit_and_subagent_paths_do_not_enter_main_cards(self):
        self.write([message("user", "goal")])
        child = self.home / "projects" / "escaped-project-name" / SID / "subagents" / "agent-child.jsonl"
        child.parent.mkdir(parents=True)
        child.write_bytes(encoded([message("user", "CHILD")]))
        registry = self.registry(name="x" * 3000, status="busy")
        collector = self.collector(self.configuration("--max-bytes", "2048"))
        view = collector.collect()
        self.assertEqual(len(view["sessions"]), 1)
        self.assertEqual(view["sessions"][0]["title"], "goal")
        self.assertTrue(view["warnings"])
        self.assertEqual(collector.adapter.metrics["registry_reads"], 0)
        metrics = dict(collector.adapter.metrics)
        collector.collect(True)
        self.assertEqual(collector.adapter.metrics, metrics)

    def test_parallel_tool_result_append_keeps_summary_continuity(self):
        prompt = message("user", "Run both checks")
        call_a = record("assistant", uuid="call-a", parentUuid=prompt["uuid"], message={"content": [
            {"type": "tool_use", "id": "tool-a", "name": "Bash", "input": {"command": "check-a"}}]})
        call_b = record("assistant", uuid="call-b", parentUuid=prompt["uuid"], message={"content": [
            {"type": "tool_use", "id": "tool-b", "name": "Bash", "input": {"command": "check-b"}}]})
        path = self.write([prompt, call_a])
        collector = self.collector()
        card = collector.collect()["sessions"][0]
        snapshot = collector.store.issue(card)
        self.append(path, [call_b, record("user", parentUuid="call-b", message={"content": [
            {"type": "tool_result", "tool_use_id": "tool-b", "content": "passed"}]})])
        card = collector.collect()["sessions"][0]
        self.assertEqual(collector.store.accept(self.payload(snapshot), {SID: card})["status"], "stale")
        self.assertEqual(card["revision"]["lineage"], snapshot["source_revision"]["lineage"])

    def test_offline_cli_isolated_import_export_and_html_injection(self):
        text = '</script><script>window.PWNED=1</script> <img src=x onerror=alert(1)>'
        self.write([message("user", text)])
        common = [sys.executable, "-I", "-B", str(SCRIPT), "--home", str(self.home),
                  "--project", str(self.project), "--runtime-dir", str(self.runtime), "--self", "observer"]
        result = subprocess.run([*common, "summary-input"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        snapshot = json.loads(result.stdout)["inputs"][0]
        payload = self.root / "summary.json"
        payload.write_text(json.dumps(self.payload(snapshot)))
        result = subprocess.run([*common, "summary-import", "--input", str(payload)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["status"], "fresh")
        output = self.root / "dashboard.html"
        result = subprocess.run([*common, "export", "--output", str(output)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = output.read_text()
        self.assertNotIn(text, document)
        self.assertIn("\\u003c/script\\u003e", document)
        self.assertIn('id="dashboard-data"', document)
        self.assertEqual(output.stat().st_mode & 0o777, 0o600)
        self.assertFalse((self.runtime / "registry.json").exists())


class ServerTests(CoreTests):
    # Only server cases belong here; inherit fixture helpers, not duplicated cases.
    def setUp(self):
        super().setUp()
        self.path = self.write([message("user", "initial goal")])
        self.common = [sys.executable, "-I", "-B", str(SCRIPT), "--home", str(self.home),
                       "--project", str(self.project), "--runtime-dir", str(self.runtime),
                       "--self", "observer", "--collect-seconds", "0.1", "--discovery-seconds", "0.1"]
        self.addCleanup(self.shutdown)

    def cli(self, command):
        result = subprocess.run([*self.common, command], capture_output=True, text=True, timeout=25)
        self.assertEqual(result.returncode, 0, result.stderr + self.log())
        return json.loads(result.stdout)

    def log(self):
        path = self.runtime / "server.log"
        return path.read_text() if path.exists() else ""

    def shutdown(self):
        subprocess.run([*self.common, "stop"], capture_output=True, timeout=15)

    def request(self, path, token=True, host=None, origin=None, method="GET"):
        registry = dashboard.read_json(self.runtime / "registry.json")
        client = http.client.HTTPConnection("127.0.0.1", registry["port"], timeout=3)
        headers = {}
        if token:
            headers["Authorization"] = "Bearer " + registry["token"]
        if host:
            headers["Host"] = host
        if origin:
            headers["Origin"] = origin
        try:
            client.request(method, path, headers=headers)
            response = client.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            client.close()

    def test_server_survives_parent_reuses_updates_and_stops(self):
        first = self.cli("start")
        self.assertFalse(first["reused"])
        self.assertIn("/#token=", first["url"])
        registry = dashboard.read_json(self.runtime / "registry.json")
        second = self.cli("start")
        self.assertTrue(second["reused"])
        self.assertEqual(first["url"], second["url"])
        self.assertEqual(self.cli("status")["status"], "running")
        self.append(self.path, [message("assistant", "separate client sees update")])
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            status, data, _ = self.request("/api/state")
            if b"separate client sees update" in data:
                break
            time.sleep(0.05)
        self.assertEqual(status, 200)
        self.assertIn(b"separate client sees update", data)
        self.assertEqual(self.cli("stop")["status"], "stopped")
        self.assertFalse((self.runtime / "registry.json").exists())
        with socket.socket() as probe:
            self.assertNotEqual(probe.connect_ex(("127.0.0.1", registry["port"])), 0)
        # A stopped process may briefly be an init-owned zombie; it must not run.
        proc = Path(f"/proc/{registry['pid']}/stat")
        deadline = time.monotonic() + 3
        while proc.exists() and proc.read_text().split()[2] != "Z" and time.monotonic() < deadline:
            time.sleep(0.05)
        self.assertTrue(not proc.exists() or proc.read_text().split()[2] == "Z")

    def test_server_concurrent_start_stale_pid_and_http_boundaries(self):
        unrelated = subprocess.Popen([sys.executable, "-I", "-c", "import time; time.sleep(30)"])
        try:
            dashboard.write_json(self.runtime / "registry.json", {"pid": unrelated.pid, "port": 1,
                                 "token": "a" * 64, "instance_id": "stale", "config_id": "stale"})
            self.assertEqual(self.cli("stop")["status"], "not_running")
            self.assertIsNone(unrelated.poll())
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: self.cli("start"), range(2)))
            self.assertEqual(results[0]["url"], results[1]["url"])
            self.assertEqual(sum(bool(result["reused"]) for result in results), 1)
            self.assertIsNone(unrelated.poll())
            self.assertEqual(self.request("/api/state", token=False)[0], 401)
            self.assertEqual(self.request("/api/health", token=False)[0], 401)
            self.assertEqual(self.request("/api/state", origin="https://hostile.example")[0], 403)
            self.assertEqual(self.request("/", host="hostile.example")[0], 403)
            for route in ("/../source.py", "/%2e%2e/source.py", "/api/state?path=/etc/passwd", "/sessions", "/config.json"):
                self.assertEqual(self.request(route)[0], 404)
            self.assertEqual(self.request("/api/shutdown", token=False, method="POST")[0], 401)
            self.assertEqual(self.request("/api/shutdown")[0], 405)
            status, _, headers = self.request("/", token=False)
            self.assertEqual(status, 200)
            self.assertNotIn("Access-Control-Allow-Origin", headers)
            self.assertIn("frame-ancestors 'none'", headers["Content-Security-Policy"])
            registry = dashboard.read_json(self.runtime / "registry.json")
            self.assertNotIn(registry["token"], self.log())
            for path in self.runtime.iterdir():
                if path.is_file():
                    self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        finally:
            unrelated.terminate()
            unrelated.wait(timeout=3)


if __name__ == "__main__":
    # Explicit loading avoids rerunning inherited core tests in ServerTests.
    suite = unittest.TestSuite()
    suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(CoreTests))
    suite.addTests(ServerTests(name) for name in ServerTests.__dict__ if name.startswith("test_"))
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
