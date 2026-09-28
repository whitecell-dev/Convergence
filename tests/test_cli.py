"""The outside adopter can use the protocol without factory concepts."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from convergence.cli import main


def run(*args):
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        code = main(list(args))
    return code, output.getvalue()


class Cli(unittest.TestCase):
    def test_hand_written_minimal_store(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            (root / "rules").mkdir(parents=True)
            (root / "rules/test.json").write_text(json.dumps({
                "id": "test", "version": 1, "scope": {"paths": ["src/"]},
                "claim": "Test is true.", "evidence_refs": []}))
            (root / "transitions.jsonl").write_text(json.dumps({
                "event": "AUTHORIZED", "id": "test", "version": 1,
                "approval_ref": "manual:human@example.com",
                "timestamp": "2026-05-13T00:00:00Z"}) + "\n")
            self.assertEqual(run("check", directory), (0, "OK\n"))
            code, status = run("status", directory)
            self.assertEqual(code, 0)
            self.assertIn("test@1 Test is true.", status)
            self.assertIn("AUTHORIZED (1)", status)
            self.assertFalse((root / "evidence").exists())
            (root / "evidence").mkdir()
            (root / "evidence/adapter-output.jsonl").write_text("adapter owned\n")
            self.assertEqual(run("check", directory), (0, "OK\n"))

    def test_cli_requires_explicit_authorization(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(run("init", directory)[0], 0)
            self.assertFalse((Path(directory) / ".convergence/evidence").exists())
            self.assertEqual(run("add", directory, "--id", "test", "--claim", "Test is true.",
                                 "--scope", "src/")[0], 0)
            root = Path(directory) / ".convergence"
            self.assertTrue((root / "rules/test/v1.json").exists())
            self.assertIn("CANDIDATE", run("status", directory)[1])
            self.assertEqual(run("activate", directory, "--id", "test", "--version", "1")[0], 1)
            self.assertEqual(run("authorize", directory, "--id", "test", "--version", "1",
                                 "--approval-ref", "MR!12")[0], 0)
            self.assertEqual(run("activate", directory, "--id", "test", "--version", "1")[0], 0)
            self.assertIn("ACTIVE (1)", run("status", directory)[1])
            self.assertEqual(run("check", directory), (0, "OK\n"))


if __name__ == "__main__":
    unittest.main()
