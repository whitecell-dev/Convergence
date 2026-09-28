"""Transition folding, multiple challenges, and retained versions."""

import json
import tempfile
import unittest
from pathlib import Path

from convergence.applicability import resolve
from convergence.claims import AuthorityStore, check_protocol_integrity, ensure_layout


class Integrity(unittest.TestCase):
    def test_challenges_cannot_be_cleared_individually(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            ensure_layout(root)
            store = AuthorityStore(root)
            store.record_rule({"id": "test", "version": 1, "scope": {},
                               "claim": "Test is true.", "evidence_refs": []})
            store.transition({"event": "AUTHORIZED", "id": "test", "version": 1,
                              "approval_ref": "email:human@example.com"})
            store.transition({"event": "ACTIVE", "id": "test", "version": 1})
            for ref in ("git:one", "git:two"):
                store.transition({"event": "CHALLENGE", "id": "test", "version": 1,
                                  "counterevidence_ref": ref})
            self.assertEqual(store.state("test", 1), "SUSPECT")
            self.assertEqual(resolve(store.rules, {}), [])
            with self.assertRaisesRegex(ValueError, "incoherent lifecycle"):
                store.transition({"event": "AUTHORIZED", "id": "test", "version": 1,
                                  "approval_ref": "PR-2", "resolves": ["git:one"]})
            self.assertEqual(store.state("test", 1), "SUSPECT")
            store.transition({"event": "AUTHORIZED", "id": "test", "version": 1,
                              "approval_ref": "PR-2", "resolves": ["git:one", "git:two"]})
            store.transition({"event": "ACTIVE", "id": "test", "version": 1})
            store.record_rule({"id": "test", "version": 2, "scope": {},
                               "claim": "Test is sometimes true.", "evidence_refs": ["git:abc:tests/test.py"]})
            with self.assertRaisesRegex(
                    ValueError, r"incoherent lifecycle transition AUTHORIZED test@2 from CANDIDATE"
                                 r"; test@1 still holds authority"):
                store.transition({"event": "AUTHORIZED", "id": "test", "version": 2,
                                  "approval_ref": "PR-3"})
            store.transition({"event": "SUPERSEDED", "id": "test", "version": 1,
                              "superseded_by": 2, "approval_ref": "PR-3"})
            store.transition({"event": "AUTHORIZED", "id": "test", "version": 2, "approval_ref": "PR-3"})
            store.transition({"event": "ACTIVE", "id": "test", "version": 2})
            self.assertEqual(store.state("test", 1), "SUPERSEDED")
            self.assertEqual(store.state("test", 2), "ACTIVE")
            self.assertEqual([r["version"] for r in resolve(store.rules, {})], [2])
            self.assertTrue((root / "rules/test/v1.json").exists())
            self.assertTrue((root / "rules/test/v2.json").exists())
            self.assertEqual(check_protocol_integrity(root), [])

    def test_invalid_content_and_events(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / ".convergence"
            ensure_layout(root)
            path = root / "rules/test.json"
            path.write_text(json.dumps({"id": "test", "version": 1, "scope": {},
                                        "evidence_refs": []}))
            self.assertTrue(any("claim needs exactly" in error for error in check_protocol_integrity(root)))
            path.write_text(json.dumps({"id": "test", "version": 1, "scope": {},
                                        "claim": " ", "evidence_refs": []}))
            self.assertTrue(any("nonblank" in error for error in check_protocol_integrity(root)))
            path.write_text(json.dumps({"id": "test", "version": 1, "scope": {},
                                        "claim": "True", "evidence_refs": []}))
            (root / "transitions.jsonl").write_text(json.dumps({
                "event": "ACTIVE", "id": "test", "version": 1}) + "\n")
            self.assertTrue(any("incoherent lifecycle" in error for error in check_protocol_integrity(root)))
            (root / "transitions.jsonl").write_text("")
            (root / "rules/test/v3.json").parent.mkdir()
            (root / "rules/test/v3.json").write_text(json.dumps({
                "id": "test", "version": 3, "scope": {},
                "claim": "Later", "evidence_refs": []}))
            self.assertTrue(any("versions must start" in error for error in check_protocol_integrity(root)))


if __name__ == "__main__":
    unittest.main()
