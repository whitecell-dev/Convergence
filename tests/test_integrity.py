"""Persisted corruption is reported without semantic execution."""

import json
import tempfile
import unittest
from pathlib import Path

from convergence.claims import AuthorityStore, append_jsonl, candidate_id, check_protocol_integrity
from convergence.evidence import record_execution
from convergence.routing import classify


class Integrity(unittest.TestCase):
    def test_corruptions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            self.assertTrue(any("missing protocol path" in error
                                for error in check_protocol_integrity(root)))
            store = AuthorityStore(root)
            rule = store.record_rule({"id": "example", "version": 1,
                "authority_state": "ACTIVE", "scope": {"paths": ["src/"]},
                "constraint": "sample", "oracle": None, "evidence_reference": None}, "PR-1")
            artifact = Path(directory) / "sample.txt"
            artifact.write_text("sample")
            result = {"rule_id": rule["id"], "rule_version": 1, "applicable": True,
                      "oracle_ran": False, "oracle_result": "unavailable"}
            execution = record_execution(root, "unit", artifact, result)
            classify(execution, root)
            self.assertEqual(check_protocol_integrity(root), [])
            rule_path = root / "rules/example.json"
            transitions_path = root / "transitions.jsonl"
            execution_path = root / "evidence/executions.jsonl"
            candidate_path = root / "evidence/discover_candidates.jsonl"

            def corruption(path, content, expected):
                original = path.read_text()
                path.write_text(content)
                self.assertTrue(any(expected in error for error in check_protocol_integrity(root)), expected)
                path.write_text(original)
                self.assertEqual(check_protocol_integrity(root), [])

            invalid_rule = json.loads(rule_path.read_text())
            invalid_rule["unknown"] = 1
            corruption(rule_path, json.dumps(invalid_rule), "unknown=['unknown']")
            corruption(transitions_path, transitions_path.read_text() + json.dumps({
                "event": "RULE_RETIRED", "rule_id": "missing", "rule_version": 1}) + "\n", "unknown rule id")
            invalid_execution = dict(execution, rule_version=99)
            corruption(execution_path, json.dumps(invalid_execution) + "\n", "unknown rule version")
            orphan = {"kind": "DISCOVER", "state": "DISCOVER", "reason": "missing execution",
                      "work_unit_id": "absent", "rule_id": None, "rule_version": None,
                      "artifact_hash": "0" * 64}
            orphan["candidate_id"] = candidate_id(orphan)
            corruption(candidate_path, candidate_path.read_text() + json.dumps(orphan) + "\n", "orphaned candidate execution")
            corruption(execution_path, execution_path.read_text() + execution_path.read_text(),
                       "duplicate execution identity")


if __name__ == "__main__":
    unittest.main()
