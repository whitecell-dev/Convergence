"""Replay both archived Click cycles without importing the archived package."""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from convergence.applicability import resolve
from convergence.claims import AuthorityStore
from convergence.click_adapter import evaluate
from convergence.compilation import compile_rules, parity
from convergence.evidence import record_execution
from convergence.routing import classify


ARCHIVE = Path(__file__).resolve().parents[2] / "Semantic-Extractor"
EXPERIMENTS = ARCHIVE / "docs/experiments"


def lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()]


def v1_from_diff() -> dict:
    diff = (EXPERIMENTS / "click-learning-cycle/authored-rule.diff").read_text()
    added = "\n".join(
        line[1:]
        for line in diff.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    )
    # The diff leaves the rule's closing brace in context rather than added lines.
    raw, _ = json.JSONDecoder().raw_decode(added[added.index("{") :] + "\n}")
    return raw


def rule_from_v1_diff() -> dict:
    raw = v1_from_diff()
    return {
        "id": raw["id"],
        "version": raw["version"],
        "scope": raw["applies_when"],
        "exclusions": raw["constraint"]["excludes"],
        "constraint": {k: v for k, v in raw["constraint"].items() if k != "excludes"},
        "instruction": raw["instruction"],
        "oracle": raw["oracle"],
        "state": "ACTIVE",
    }


class ClickCycles(unittest.TestCase):
    def test_learning_then_maintenance_from_clean_state(self):
        fixture = json.loads(
            (ARCHIVE / "Python/IR-files/calyx_click_v6.json").read_text()
        )
        before = lines(EXPERIMENTS / "click-learning-cycle/before/executions.jsonl")[0]
        saved_discover = lines(
            EXPERIMENTS / "click-learning-cycle/before/discovery_candidates.jsonl"
        )[0]
        after = {
            r["work_unit_id"]: r
            for r in lines(EXPERIMENTS / "click-learning-cycle/after/executions.jsonl")
        }
        post = {
            r["work_unit_id"]: r
            for r in lines(
                EXPERIMENTS / "click-maintenance/post_decision/executions.jsonl"
            )
        }
        decision = json.loads(
            (EXPERIMENTS / "click-maintenance/revalidation_record.json").read_text()
        )
        note = (
            ARCHIVE / "docs/solutions/workflow-issues/click-option-only-capture.md"
        ).read_text()
        self.assertIn("human semantic author explicitly accepted", note)
        self.assertEqual(decision["human_decision"], "REVISED")
        self.assertEqual(before["outcome"], "unresolved")
        self.assertEqual(saved_discover["stage"], "DISCOVER")

        sources = {
            "unknown1": EXPERIMENTS / "click-feedback/unknown.py",
            "same_class1": EXPERIMENTS / "click-learning-cycle/same_class.py",
            "negative1": EXPERIMENTS / "click-learning-cycle/negative.py",
            "challenge": EXPERIMENTS / "click-maintenance/expose_value_false.py",
        }
        with tempfile.TemporaryDirectory() as scratch:
            state = Path(scratch)
            store = AuthorityStore(state / "authority")
            evidence = state / "evidence"

            def run(name, rule, saved):
                observation = evaluate(sources[name], rule)
                record = record_execution(
                    evidence,
                    name,
                    sources[name],
                    observation,
                    authorized_rules=store.rules,
                    expected_hash=saved["artifact_sha256"],
                )
                routed = classify(record, evidence)
                self.assertEqual(record["outcome"].lower(), saved["outcome"])
                return record, routed

            # Cycle A: the saved unresolved WorkUnit creates a candidate.
            initial, candidate = run("unknown1", None, before)
            self.assertEqual(initial["outcome"], "UNRESOLVED")
            self.assertEqual(candidate["kind"], "DISCOVER")
            self.assertEqual(len(lines(evidence / "discovery_candidates.jsonl")), 1)

            v1 = rule_from_v1_diff()
            self.assertEqual(v1["version"], 1)
            with self.assertRaises(ValueError):
                store.record_rule(v1, "")
            approved_v1 = store.record_rule(
                v1, str(EXPERIMENTS / "click-learning-cycle/authored-rule.diff")
            )
            self.assertEqual(approved_v1["state"], "ACTIVE")
            self.assertEqual(
                len(resolve(store.rules, "click", "option", "generate")), 1
            )
            self.assertEqual(resolve(store.rules, "click", "argument", "generate"), [])
            bundle_v1 = compile_rules(store.rules, fixture)
            self.assertTrue(all(parity(bundle_v1, fixture).values()))
            self.assertEqual(bundle_v1["WR"][0], v1_from_diff())
            self.assertEqual(bundle_v1["WR"][0]["version"], 1)
            self.assertEqual(
                bundle_v1["WR"][0]["constraint"]["excludes"], v1["exclusions"]
            )
            self.assertEqual(bundle_v1["oracle_specs"][0]["oracle"], v1["oracle"])
            self.assertEqual(
                bundle_v1["generator_constraints"][0]["exclusions"], v1["exclusions"]
            )
            for name, outcome in (
                ("unknown1", "PROVEN"),
                ("same_class1", "PROVEN"),
                ("negative1", "VIOLATED"),
            ):
                record, _ = run(name, approved_v1, after[name])
                self.assertEqual(record["outcome"], outcome)
            self.assertEqual(len(lines(evidence / "discovery_candidates.jsonl")), 1)

            # Cycle B: the v1 claim applies, but the oracle cannot support it.
            challenge_saved = lines(
                EXPERIMENTS / "click-maintenance/suspect/executions.jsonl"
            )[0]
            challenged, suspect = run("challenge", approved_v1, challenge_saved)
            self.assertEqual(
                (
                    challenged["outcome"],
                    challenged["applicable"],
                    challenged["oracle_ran"],
                ),
                ("UNRESOLVED", True, False),
            )
            self.assertEqual(suspect["kind"], "REVALIDATE")
            self.assertEqual(suspect["state"], "SUSPECT")
            self.assertEqual(len(lines(evidence / "revalidation_candidates.jsonl")), 1)

            revision = (EXPERIMENTS / "click-maintenance/revision.diff").read_text()
            self.assertIn('+      "version": 2,', revision)
            self.assertIn('"expose_value=False"]', revision)
            v2 = copy.deepcopy(v1)
            v2["version"] = 2
            v2["exclusions"].append("expose_value=False")
            approved_v2 = store.record_rule(
                v2, str(EXPERIMENTS / "click-maintenance/revision.diff")
            )
            self.assertEqual(approved_v2["state"], "ACTIVE")
            self.assertEqual(store.rules[0]["state"], "RETIRED")
            with self.assertRaises(ValueError):
                record_execution(
                    evidence,
                    "stale",
                    sources["unknown1"],
                    evaluate(sources["unknown1"], approved_v1),
                    store.rules,
                )
            self.assertEqual(
                [
                    r["version"]
                    for r in resolve(store.rules, "click", "option", "generate")
                ],
                [2],
            )
            authored = json.loads(
                (
                    ARCHIVE
                    / "Python/boilerplate-generator/semantic/tables/click/invariants.json"
                ).read_text()
            )
            self.assertEqual(
                compile_rules(store.rules, fixture)["WR"][0],
                authored["worker_rules"][2],
            )
            bundle_v2 = compile_rules(store.rules, fixture)
            self.assertTrue(all(parity(bundle_v2, fixture).values()))
            for name, outcome in (
                ("unknown1", "PROVEN"),
                ("same_class1", "PROVEN"),
                ("negative1", "VIOLATED"),
                ("challenge", "UNRESOLVED"),
            ):
                record, routed = run(name, approved_v2, post[name])
                self.assertEqual(record["outcome"], outcome)
                if name == "challenge":
                    self.assertFalse(record["applicable"])
                    self.assertEqual(routed["kind"], "DISCOVER")
            self.assertEqual(len(lines(evidence / "discovery_candidates.jsonl")), 2)
            self.assertEqual(len(lines(evidence / "revalidation_candidates.jsonl")), 1)
            self.assertEqual(len(lines(evidence / "executions.jsonl")), 9)


if __name__ == "__main__":
    unittest.main()
