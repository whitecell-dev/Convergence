"""The CLI wraps the protocol; it adds no responsibility of its own."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path

from convergence.cli import main
from convergence.claims import AuthorityStore
from convergence.evidence import record_execution
from convergence.routing import classify


def run(*argv) -> tuple[int, str]:
    """Call the CLI the way the console script does and capture its output."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        code = main(list(argv))
    return code, out.getvalue()


class Cli(unittest.TestCase):
    def setUp(self):
        previous = Path.cwd()
        self.addCleanup(os.chdir, previous)
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        os.chdir(directory.name)
        self.root = Path(".convergence")

    def add_uuid_rule(self):
        return run("add", "--id", "api.user-id-format",
                   "--constraint", "User IDs are UUIDv7.",
                   "--scope", '{"paths":["src/api/"]}',
                   "--approval", "PR-381")

    def test_init_creates_the_documented_layout(self):
        code, out = run("init")
        self.assertEqual(code, 0)
        for relative in ("README.md", "rules", "transitions.jsonl", "evidence",
                         "evidence/executions.jsonl", "evidence/discover_candidates.jsonl",
                         "evidence/revalidate_candidates.jsonl"):
            self.assertTrue((self.root / relative).exists(), relative)
        self.assertIn("created .convergence/rules", out)
        self.assertIn("convergence add", out)

    def test_init_is_idempotent(self):
        self.assertEqual(run("init")[0], 0)
        code, out = run("init")
        self.assertEqual(code, 0)
        self.assertIn("already present", out)
        self.assertNotIn("created", out)
        code, out = run("check")
        self.assertEqual((code, out.strip()), (0, "OK"))

    def test_add_writes_rule_content_and_transitions(self):
        run("init")
        code, out = self.add_uuid_rule()
        self.assertEqual(code, 0)
        saved = json.loads((self.root / "rules/api.user-id-format.json").read_text())
        self.assertEqual(saved["version"], 1)
        self.assertEqual(saved["constraint"], "User IDs are UUIDv7.")
        self.assertEqual(saved["scope"], {"paths": ["src/api/"]})
        self.assertIsNone(saved["oracle"])
        self.assertNotIn("authority_state", saved)
        events = [json.loads(line) for line in
                  (self.root / "transitions.jsonl").read_text().splitlines()]
        self.assertEqual([row["event"] for row in events], ["RULE_RECORDED", "RULE_ACTIVE"])
        self.assertEqual(events[0]["approval_reference"], "PR-381")
        self.assertIn("api.user-id-format v1 ACTIVE", out)

    def test_status_reports_the_rule_as_active(self):
        run("init")
        self.add_uuid_rule()
        code, out = run("status")
        self.assertEqual(code, 0)
        self.assertIn("ACTIVE (1)", out)
        self.assertIn("api.user-id-format v1", out)
        self.assertIn('"paths": ["src/api/"]', out)
        self.assertIn("counts: ACTIVE=1 SUSPECT=0 RETIRED=0", out)

    def test_status_reports_verification_unavailable_without_an_oracle(self):
        run("init")
        self.assertIn("mechanical verification: unavailable", self.add_uuid_rule()[1])
        code, out = run("status")
        self.assertEqual(code, 0)
        self.assertIn("verification=UNAVAILABLE", out)

    def test_status_on_an_empty_store_points_at_add(self):
        run("init")
        code, out = run("status")
        self.assertEqual(code, 0)
        self.assertIn("no rules recorded yet", out)
        self.assertIn("convergence add", out)

    def test_check_is_ok_on_a_clean_store(self):
        run("init")
        self.add_uuid_rule()
        code, out = run("check")
        self.assertEqual((code, out.strip()), (0, "OK"))

    def test_status_names_the_candidate_that_challenged_a_suspect_rule(self):
        run("init")
        self.add_uuid_rule()
        store = AuthorityStore(Path(".convergence"))
        store.record_rule({"id": "api.user-id-format", "version": 2,
                           "authority_state": "ACTIVE", "scope": {"paths": ["src/api/"]},
                           "constraint": "User IDs are UUIDv7.", "oracle": "pytest",
                           "evidence_reference": "tests/test_user_ids.py"}, "PR-512")
        Path("sample.py").write_text("uid = 1\n")
        execution = record_execution(Path(".convergence"), "sample", Path("sample.py"),
                                     {"rule_id": "api.user-id-format", "rule_version": 2,
                                      "applicable": True, "oracle_ran": False,
                                      "oracle_result": "unavailable"})
        candidate = classify(execution, Path(".convergence"))
        code, out = run("status")
        self.assertEqual(code, 0)
        self.assertIn("SUSPECT (1)", out)
        self.assertIn(f"challenged by candidate {candidate['candidate_id'][:12]}", out)
        self.assertIn("open candidates (1)", out)
        self.assertIn("counts: ACTIVE=0 SUSPECT=1 RETIRED=0", out)

    def test_check_names_the_file_it_concerns(self):
        run("init")
        self.add_uuid_rule()
        (self.root / "rules/broken.json").write_text(json.dumps({
            "id": "broken", "version": 1, "scope": {}, "constraint": "x",
            "oracle": None, "evidence_reference": None, "surprise": 1}))
        code, out = run("check")
        self.assertEqual(code, 1)
        self.assertIn("broken.json", out)
        self.assertIn("unknown=['surprise']", out)
        self.assertNotEqual(out.strip(), "OK")


if __name__ == "__main__":
    unittest.main()
