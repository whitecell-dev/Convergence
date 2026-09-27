"""A generic authorized claim needs neither Click nor an oracle."""

import json
import tempfile
import unittest
from pathlib import Path

from convergence.applicability import resolve
from convergence.claims import AuthorityStore, check_protocol_integrity, read_jsonl
from convergence.evidence import record_execution
from convergence.routing import classify


class GenericClaim(unittest.TestCase):
    def test_uuidv7_authority_without_oracle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            store = AuthorityStore(root)
            rule = {"id": "api.user-id-format", "version": 1,
                    "authority_state": "ACTIVE", "scope": {"paths": ["src/api/"]},
                    "constraint": "User IDs are UUIDv7", "oracle": None,
                    "evidence_reference": "tests/test_user_ids.py"}
            saved = store.record_rule(rule, "PR-381")
            path = root / "rules/api.user-id-format.json"
            self.assertTrue(path.exists())
            for relative in ("README.md", "transitions.jsonl", "evidence/executions.jsonl",
                             "evidence/discover_candidates.jsonl", "evidence/revalidate_candidates.jsonl"):
                self.assertTrue((root / relative).exists(), relative)
            self.assertIsNone(json.loads(path.read_text())["oracle"])
            self.assertEqual([row["event"] for row in read_jsonl(root / "transitions.jsonl")],
                             ["RULE_RECORDED", "RULE_ACTIVE"])
            reloaded = AuthorityStore(root)
            self.assertEqual(reloaded.rules[0]["authority_state"], "ACTIVE")
            self.assertEqual(reloaded.rules[0]["approval_reference"], "PR-381")
            self.assertEqual(reloaded.rules[0]["evidence_reference"], "tests/test_user_ids.py")
            self.assertEqual(resolve(reloaded.rules, {"paths": ["src/api/"]}), [saved])
            self.assertEqual(resolve(reloaded.rules, {"paths": ["src/other/"]}), [])
            self.assertEqual(resolve(reloaded.rules, "src/api/users.py",
                                     lambda scope, path: path.startswith(scope["paths"][0])), [saved])
            self.assertIsNone(reloaded.rules[0]["oracle"])
            rule_bytes = path.read_bytes()
            self.assertEqual(reloaded.status()["rules"][0]["verification"], "UNAVAILABLE")
            self.assertEqual(reloaded.status()["counts"]["ACTIVE"], 1)
            artifact = Path(directory) / "sample.txt"
            artifact.write_text("sample")
            result = {"rule_id": saved["id"], "rule_version": 1, "applicable": True,
                      "oracle_ran": False, "oracle_result": "unavailable"}
            with self.assertRaisesRegex(ValueError, "no oracle"):
                record_execution(root, "false-proof", artifact,
                                 dict(result, oracle_ran=True, oracle_result="pass"))
            execution = record_execution(root, "sample", artifact, result)
            self.assertEqual(execution["outcome"], "UNRESOLVED")
            self.assertEqual(classify(execution, root)["kind"], "DISCOVER")
            self.assertEqual(path.read_bytes(), rule_bytes)
            self.assertEqual(AuthorityStore(root).state(saved["id"], 1), "ACTIVE")
            self.assertEqual(check_protocol_integrity(root), [])


if __name__ == "__main__":
    unittest.main()
