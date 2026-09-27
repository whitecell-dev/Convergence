"""Replays return persisted evidence and candidate identities."""

import tempfile
import unittest
from pathlib import Path

from convergence.claims import AuthorityStore, check_protocol_integrity, read_jsonl
from convergence.evidence import record_execution
from convergence.routing import classify


class Idempotence(unittest.TestCase):
    def test_duplicate_then_resolution_then_distinct_challenge(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            store = AuthorityStore(root)
            rule = store.record_rule({"id": "api.user-id-format", "version": 1,
                "authority_state": "ACTIVE", "scope": {"paths": ["src/api/"]},
                "constraint": "User IDs are UUIDv7", "oracle": "check_uuidv7.py",
                "evidence_reference": "tests/test_user_ids.py"}, "PR-381")
            artifact = Path(directory) / "sample.txt"
            artifact.write_text("sample")
            result = {"rule_id": rule["id"], "rule_version": 1, "applicable": True,
                      "oracle_ran": False, "oracle_result": "unavailable"}
            first = record_execution(root, "unit-1", artifact, result)
            candidate = classify(first, root)
            self.assertEqual(candidate["kind"], "REVALIDATE")
            second = record_execution(root, "unit-1", artifact, result)
            self.assertEqual(second, first)
            self.assertEqual(classify(second, root), candidate)
            self.assertEqual(len(read_jsonl(root / "evidence/executions.jsonl")), 1)
            self.assertEqual(len(read_jsonl(root / "evidence/revalidate_candidates.jsonl")), 1)
            self.assertEqual(sum(row["event"] == "RULE_CHALLENGED" for row in
                                 read_jsonl(root / "transitions.jsonl")), 1)
            store.reload()
            self.assertEqual(store.state(rule["id"], 1), "SUSPECT")
            store.resolve_candidate(candidate["candidate_id"], "ACTIVE", "PR-382")
            self.assertEqual(store.status()["open_candidates"], [])
            self.assertEqual(store.state(rule["id"], 1), "ACTIVE")
            other = record_execution(root, "unit-2", artifact, result)
            new_candidate = classify(other, root)
            self.assertNotEqual(candidate["candidate_id"], new_candidate["candidate_id"])
            self.assertEqual(len(read_jsonl(root / "evidence/revalidate_candidates.jsonl")), 2)
            self.assertEqual(len(store.status()["open_candidates"]), 1)
            self.assertEqual(check_protocol_integrity(root), [])


if __name__ == "__main__":
    unittest.main()
