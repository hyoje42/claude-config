#!/usr/bin/env python3
"""Exercise the digest CLI using isolated transcripts and a temporary tool home."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "home/skills/inspect-session/scripts/session_digest.py"


class StateOpsTests(unittest.TestCase):
    def overview(self, command, result="", error=False, **extra):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.jsonl"
            rows = [
                {"type": "assistant", "uuid": "a", "message": {"content": [
                    {"type": "tool_use", "id": "call", "name": "Bash", "input": {"command": command}}]}},
                {"type": "user", "uuid": "b", "parentUuid": "a", "toolUseResult": extra,
                 "message": {"content": [{"type": "tool_result", "tool_use_id": "call",
                                          "content": result, "is_error": error}]}},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows))
            env = dict(os.environ, CLAUDE_CONFIG_DIR=directory)
            proc = subprocess.run([sys.executable, "-B", str(SCRIPT), "overview", str(path)],
                                  env=env, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return proc.stdout

    def test_quoted_text_comments_and_heredoc_bodies_are_not_commands(self):
        for command in [
            "printf '%s\\n' 'git push origin main; git reset --hard'",
            'echo "text\ngit push origin main\ntext"',
            "# git push origin main\ngit status",
            "cat <<'EOF'\ngit push origin main\nEOF",
            "claude-sync-to-home --dry-run",
        ]:
            with self.subTest(command=command):
                out = self.overview(command)
                self.assertNotIn("state ops", out)
                self.assertNotIn("git·sync 명령 후보", out)

    def test_commands_after_keywords_prefixes_and_mid_word_hash_are_detected(self):
        for command in [
            "curl http://x/#a; git push",
            "echo a#b && git push",
            "if true; then git commit -m x; fi",
            "for r in a b; do git push origin $r; done",
            "{ git push; }",
            "! git push",
            "sudo -u me git push",
            "env FOO=1 git push",
            "git --no-pager -C dir push",
            "git pull --rebase",
            "bash ./claude-sync-to-home",
        ]:
            with self.subTest(command=command):
                self.assertIn("git·sync 명령 후보", self.overview(command))

    def test_hash_at_word_start_is_still_a_comment(self):
        for command in ["echo hi # git push", "echo hi;# git push"]:
            with self.subTest(command=command):
                self.assertNotIn("git·sync 명령 후보", self.overview(command))

    def test_compound_call_keeps_conditions_and_labels_only_call_result(self):
        command = "false && git push origin main; true"
        out = self.overview(command)
        self.assertIn("개별 실행 여부는 미확인", out)
        self.assertIn("호출 정상 반환  " + command, out)

    def test_background_and_interrupted_calls_are_not_success(self):
        out = self.overview("git push origin main", backgroundTaskId="task-1")
        self.assertIn("백그라운드 실행  git push", out)
        out = self.overview("git push origin main", interrupted=True)
        self.assertIn("중단됨  git push", out)

    def test_git_options_and_commit_heredoc_are_detected(self):
        out = self.overview("git -C '/tmp/project dir' commit -F - <<'EOF'\nfix: git push race\nEOF")
        section = out.split("git·sync 명령 후보를 포함한 셸 호출", 1)[1].split("\n\n", 1)[0]
        self.assertIn("git -C '/tmp/project dir' commit", section)
        self.assertNotIn("race", section)


if __name__ == "__main__":
    unittest.main()
