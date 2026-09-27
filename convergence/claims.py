"""Approval-gated rule content and append-only lifecycle events."""

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

RULE_REQUIRED = {"id", "version", "scope", "constraint", "oracle", "evidence_reference"}
RULE_OPTIONAL = {"exclusions", "instruction"}
EVENTS = {"RULE_RECORDED", "RULE_ACTIVE", "RULE_CHALLENGED", "RULE_REVISED", "RULE_RETIRED", "CANDIDATE_RESOLVED"}
EVENT_FIELDS = {
    "RULE_RECORDED": {"event", "rule_id", "rule_version", "approval_reference"},
    "RULE_ACTIVE": {"event", "rule_id", "rule_version"},
    "RULE_CHALLENGED": {"event", "rule_id", "rule_version", "candidate_id"},
    "RULE_REVISED": {"event", "rule_id", "rule_version", "new_version"},
    "RULE_RETIRED": {"event", "rule_id", "rule_version"},
    "CANDIDATE_RESOLVED": {"event", "candidate_id", "resolution", "approval_reference"},
}


def ensure_layout(root):
    root = Path(root)
    (root / "rules").mkdir(parents=True, exist_ok=True)
    (root / "evidence").mkdir(parents=True, exist_ok=True)
    readme = root / "README.md"
    if not readme.exists():
        readme.write_text("# Convergence\n\nRules contain current claim content. "
                          "transitions.jsonl records authority changes. "
                          "evidence/ contains append-only executions and candidates.\n",
                          encoding="utf-8")
    for relative in ("transitions.jsonl", "evidence/executions.jsonl",
                     "evidence/discover_candidates.jsonl", "evidence/revalidate_candidates.jsonl"):
        (root / relative).touch(exist_ok=True)


def read_jsonl(path):
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path.name}:{number}: invalid JSON") from exc
    return rows


def append_jsonl(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


def execution_identity(row):
    return tuple(row[key] for key in ("work_unit_id", "rule_id", "rule_version", "artifact_hash"))


def candidate_identity(row):
    return (row["kind"],) + execution_identity(row)


def candidate_id(row):
    payload = json.dumps(candidate_identity(row), separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def validate_rule(rule, *, input_rule=False):
    if not isinstance(rule, dict):
        raise ValueError("rule must be an object")
    expected = RULE_REQUIRED | RULE_OPTIONAL | ({"authority_state"} if input_rule else set())
    missing = RULE_REQUIRED - rule.keys()
    unknown = rule.keys() - expected
    if missing or unknown or (input_rule and rule.get("authority_state") != "ACTIVE"):
        raise ValueError(f"invalid rule fields: missing={sorted(missing)}, unknown={sorted(unknown)}")
    if not isinstance(rule["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", rule["id"]):
        raise ValueError("invalid rule id")
    if type(rule["version"]) is not int or rule["version"] < 1:
        raise ValueError("invalid rule version")
    if not isinstance(rule["scope"], dict):
        raise ValueError("scope must be an object")
    if not isinstance(rule["constraint"], (str, dict)) or not rule["constraint"]:
        raise ValueError("constraint must be nonempty text or object")
    for field in ("oracle", "evidence_reference"):
        value = rule[field]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise ValueError(f"{field} must be null or nonempty text")
    if "exclusions" in rule and (not isinstance(rule["exclusions"], list) or not all(isinstance(x, str) for x in rule["exclusions"])):
        raise ValueError("exclusions must be a list of text")
    if "instruction" in rule and not isinstance(rule["instruction"], str):
        raise ValueError("instruction must be text")


def fold(transitions):
    states = {}
    approvals = {}
    resolved = set()
    for event in transitions:
        kind = event["event"]
        if kind == "CANDIDATE_RESOLVED":
            resolved.add(event["candidate_id"])
            continue
        key = (event["rule_id"], event["rule_version"])
        if kind == "RULE_RECORDED":
            states[key] = "CANDIDATE"
            approvals[key] = event["approval_reference"]
        elif kind == "RULE_ACTIVE":
            states[key] = "ACTIVE"
        elif kind == "RULE_CHALLENGED":
            states[key] = "SUSPECT"
        elif kind == "RULE_RETIRED":
            states[key] = "RETIRED"
    return states, approvals, resolved


class AuthorityStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.rule_dir = self.root / "rules"
        self.transition_path = self.root / "transitions.jsonl"
        self.reload()

    def reload(self):
        self.transitions = read_jsonl(self.transition_path)
        self.states, self.approvals, self.resolved = fold(self.transitions)
        self.rules = []
        for path in sorted(self.rule_dir.glob("*.json")):
            rule = json.loads(path.read_text(encoding="utf-8"))
            validate_rule(rule)
            if path.stem != rule["id"]:
                raise ValueError(f"{path.name}: rule id differs from filename")
            key = (rule["id"], rule["version"])
            if key not in self.states or key not in self.approvals:
                raise ValueError(f"{path.name}: missing recorded transition")
            self.rules.append({**rule, "authority_state": self.states[key], "approval_reference": self.approvals[key]})
        return self.rules

    def state(self, rule_id, version):
        return self.states.get((rule_id, version))

    def _candidates(self):
        return [*read_jsonl(self.root / "evidence/discover_candidates.jsonl"),
                *read_jsonl(self.root / "evidence/revalidate_candidates.jsonl")]

    def status(self):
        self.reload()
        open_candidates = [row for row in self._candidates() if row["candidate_id"] not in self.resolved]
        rules = [{"id": row["id"], "version": row["version"],
                  "authority_state": row["authority_state"],
                  "verification": "UNAVAILABLE" if row["oracle"] is None else "ORACLE_DECLARED"}
                 for row in self.rules]
        return {"rules": rules, "open_candidates": open_candidates,
                "counts": {state: sum(row["authority_state"] == state for row in rules)
                           for state in ("ACTIVE", "SUSPECT", "RETIRED")}}

    def record_rule(self, rule: dict, approval_reference: str) -> dict:
        if not isinstance(approval_reference, str) or not approval_reference.strip():
            raise ValueError("human approval reference required")
        validate_rule(rule, input_rule=True)
        prior = next((old for old in self.rules if old["id"] == rule["id"]), None)
        if rule["version"] != (prior["version"] + 1 if prior else 1):
            raise ValueError("rule version must start at 1 and advance by one")
        content = {key: value for key, value in rule.items() if key != "authority_state"}
        try:
            serialized = json.dumps(content, sort_keys=True, indent=2)
        except (TypeError, ValueError) as exc:
            raise ValueError("rule must be JSON serializable") from exc
        ensure_layout(self.root)
        target = self.rule_dir / f"{rule['id']}.json"
        # ponytail: single-writer file protocol; concurrent writers need an external Git lock or transaction.
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.rule_dir, prefix=".rule-", delete=False) as stream:
            stream.write(serialized + "\n")
            temporary = stream.name
        os.replace(temporary, target)
        if prior:
            old = {"rule_id": prior["id"], "rule_version": prior["version"]}
            append_jsonl(self.transition_path, {"event": "RULE_REVISED", **old, "new_version": rule["version"]})
            append_jsonl(self.transition_path, {"event": "RULE_RETIRED", **old})
            for candidate in self._candidates():
                if candidate["kind"] == "REVALIDATE" and candidate["rule_id"] == prior["id"] and candidate["rule_version"] == prior["version"] and candidate["candidate_id"] not in self.resolved:
                    append_jsonl(self.transition_path, {"event": "CANDIDATE_RESOLVED", "candidate_id": candidate["candidate_id"], "resolution": "REVISED", "approval_reference": approval_reference})
        key = {"rule_id": rule["id"], "rule_version": rule["version"]}
        append_jsonl(self.transition_path, {"event": "RULE_RECORDED", **key, "approval_reference": approval_reference})
        append_jsonl(self.transition_path, {"event": "RULE_ACTIVE", **key})
        self.reload()
        return self.rules[[r["id"] for r in self.rules].index(rule["id"])]

    def resolve_candidate(self, candidate_id_value: str, resolution: str, approval_reference: str):
        if not isinstance(approval_reference, str) or not approval_reference.strip():
            raise ValueError("human approval reference required")
        if resolution not in {"ACTIVE", "REVISED", "RETIRED"}:
            raise ValueError("invalid candidate resolution")
        candidates = [row for row in self._candidates() if row["candidate_id"] == candidate_id_value]
        if len(candidates) != 1 or candidate_id_value in self.resolved:
            raise ValueError("candidate missing or already resolved")
        candidate = candidates[0]
        if resolution == "REVISED" and not any(event["event"] == "RULE_REVISED" and event["rule_id"] == candidate["rule_id"] and event["rule_version"] == candidate["rule_version"] for event in self.transitions):
            raise ValueError("revision has not been recorded")
        append_jsonl(self.transition_path, {"event": "CANDIDATE_RESOLVED", "candidate_id": candidate_id_value, "resolution": resolution, "approval_reference": approval_reference})
        if candidate["kind"] == "REVALIDATE" and resolution in {"ACTIVE", "RETIRED"}:
            append_jsonl(self.transition_path, {"event": "RULE_ACTIVE" if resolution == "ACTIVE" else "RULE_RETIRED", "rule_id": candidate["rule_id"], "rule_version": candidate["rule_version"]})
        self.reload()



def _integrity_files(root, errors):
    required_paths = ("README.md", "rules", "transitions.jsonl", "evidence",
                      "evidence/executions.jsonl", "evidence/discover_candidates.jsonl",
                      "evidence/revalidate_candidates.jsonl")
    for relative in required_paths:
        path = root / relative
        valid = path.is_dir() if relative in {"rules", "evidence"} else path.is_file()
        if not valid:
            errors.append(f"missing protocol path: {relative}")
    rules = {}
    for path in sorted((root / "rules").glob("*.json")):
        try:
            rule = json.loads(path.read_text(encoding="utf-8"))
            validate_rule(rule)
            if path.stem != rule["id"]:
                raise ValueError("rule id differs from filename")
            rules[rule["id"]] = rule
        except (ValueError, json.JSONDecodeError) as exc:
            errors.append(f"{path.name}: {exc}")

    def rows(path):
        if not path.is_file():
            return []
        try:
            return read_jsonl(path)
        except ValueError as exc:
            errors.append(str(exc))
            return []

    return (rules, rows(root / "transitions.jsonl"),
            rows(root / "evidence/executions.jsonl"),
            [*rows(root / "evidence/discover_candidates.jsonl"),
             *rows(root / "evidence/revalidate_candidates.jsonl")])


def _integrity_transitions(rules, transitions, candidates, errors):
    candidate_by_id = {row["candidate_id"]: row for row in candidates
                       if isinstance(row, dict) and isinstance(row.get("candidate_id"), str)}
    recorded, versions, states, challenged, resolved, revisions = set(), {}, {}, set(), set(), []
    for number, event in enumerate(transitions, 1):
        label = f"transitions.jsonl:{number}"
        if not isinstance(event, dict) or not isinstance(event.get("event"), str) or event["event"] not in EVENTS:
            errors.append(f"{label}: unknown transition event")
            continue
        kind = event["event"]
        if set(event) != EVENT_FIELDS[kind]:
            errors.append(f"{label}: invalid transition fields")
        if kind == "CANDIDATE_RESOLVED":
            cid = event.get("candidate_id")
            if not isinstance(cid, str):
                errors.append(f"{label}: invalid candidate reference")
                continue
            if cid not in candidate_by_id:
                errors.append(f"{label}: orphaned candidate resolution")
            if cid in resolved:
                errors.append(f"{label}: duplicate candidate resolution")
            if candidate_by_id.get(cid, {}).get("kind") == "REVALIDATE" and cid not in challenged:
                errors.append(f"{label}: resolution precedes challenge")
            resolved.add(cid)
            if event.get("resolution") not in {"ACTIVE", "REVISED", "RETIRED"} or not isinstance(event.get("approval_reference"), str) or not event["approval_reference"].strip():
                errors.append(f"{label}: invalid candidate resolution")
            continue
        rule_id, version = event.get("rule_id"), event.get("rule_version")
        if not isinstance(rule_id, str) or type(version) is not int:
            errors.append(f"{label}: invalid rule reference")
            continue
        key = (rule_id, version)
        if rule_id not in rules:
            errors.append(f"{label}: unknown rule id")
        if kind == "RULE_RECORDED":
            if key in recorded:
                errors.append(f"{label}: duplicate RULE_RECORDED")
            if version != versions.get(rule_id, 0) + 1:
                errors.append(f"{label}: incoherent rule version history")
            if not isinstance(event.get("approval_reference"), str) or not event["approval_reference"].strip():
                errors.append(f"{label}: missing approval reference")
            recorded.add(key)
            versions[rule_id] = version
            states[key] = "CANDIDATE"
            continue
        if key not in recorded:
            errors.append(f"{label}: orphaned rule version or event precedes RULE_RECORDED")
        previous = states.get(key)
        allowed = {"RULE_ACTIVE": {"CANDIDATE", "SUSPECT"},
                   "RULE_CHALLENGED": {"ACTIVE", "SUSPECT"},
                   "RULE_REVISED": {"ACTIVE", "SUSPECT"},
                   "RULE_RETIRED": {"ACTIVE", "SUSPECT"}}
        if previous not in allowed[kind]:
            errors.append(f"{label}: incoherent lifecycle transition")
        if kind == "RULE_ACTIVE":
            states[key] = "ACTIVE"
        elif kind == "RULE_RETIRED":
            states[key] = "RETIRED"
        elif kind == "RULE_CHALLENGED":
            cid = event.get("candidate_id")
            if not isinstance(cid, str):
                errors.append(f"{label}: invalid candidate reference")
                continue
            candidate = candidate_by_id.get(cid)
            if candidate is None:
                errors.append(f"{label}: orphaned challenge transition")
            elif candidate.get("kind") != "REVALIDATE" or (candidate.get("rule_id"), candidate.get("rule_version")) != key:
                errors.append(f"{label}: challenge candidate mismatch")
            challenged.add(cid)
            states[key] = "SUSPECT"
        elif kind == "RULE_REVISED":
            revisions.append((label, rule_id, event.get("new_version")))
    for label, rule_id, new_version in revisions:
        if type(new_version) is not int or (rule_id, new_version) not in recorded:
            errors.append(f"{label}: orphaned revision target")
    for rule_id, rule in rules.items():
        key = (rule_id, rule["version"])
        if key not in recorded:
            errors.append(f"{rule_id}.json: current version has no RULE_RECORDED")
        if rule["version"] != versions.get(rule_id):
            errors.append(f"{rule_id}.json: current version differs from transition history")
        if states.get(key) not in {"ACTIVE", "SUSPECT", "RETIRED"}:
            errors.append(f"{rule_id}.json: current version has no settled authority state")
    return recorded, challenged


def _integrity_executions(executions, recorded, errors):
    by_key = {}
    required = {"work_unit_id", "rule_id", "rule_version", "artifact_hash", "applicable", "oracle_ran", "oracle_result", "outcome"}
    for number, row in enumerate(executions, 1):
        label = f"executions.jsonl:{number}"
        if not isinstance(row, dict) or set(row) != required:
            errors.append(f"{label}: invalid execution fields")
            continue
        if (not isinstance(row["work_unit_id"], str)
                or (row["rule_id"] is not None and not isinstance(row["rule_id"], str))
                or (row["rule_version"] is not None and type(row["rule_version"]) is not int)
                or not isinstance(row["artifact_hash"], str)
                or not re.fullmatch(r"[0-9a-f]{64}", row["artifact_hash"])
                or type(row["applicable"]) is not bool or type(row["oracle_ran"]) is not bool
                or not isinstance(row["oracle_result"], str)
                or row["oracle_result"] not in {"pass", "violated", "unavailable", "not_applicable"}
                or not isinstance(row["outcome"], str)
                or row["outcome"] not in {"PROVEN", "VIOLATED", "UNRESOLVED"}):
            errors.append(f"{label}: invalid execution values")
            continue
        key = execution_identity(row)
        if key in by_key:
            errors.append(f"{label}: duplicate execution identity")
        by_key[key] = row
        if row["rule_id"] is not None and (row["rule_id"], row["rule_version"]) not in recorded:
            errors.append(f"{label}: unknown rule version")
        if row["rule_id"] is None and row["rule_version"] is not None:
            errors.append(f"{label}: rule version without rule id")
        expected = "VIOLATED" if row["oracle_result"] == "violated" else "PROVEN" if row["oracle_result"] == "pass" else "UNRESOLVED"
        if (row["outcome"] != expected or row["oracle_ran"] != (row["oracle_result"] in {"pass", "violated"})
                or (expected != "UNRESOLVED" and not row["applicable"])):
            errors.append(f"{label}: inconsistent oracle outcome")
    return by_key


def _integrity_candidates(candidates, executions, challenged, errors):
    seen, routed = set(), set()
    required = {"candidate_id", "kind", "state", "reason", "work_unit_id", "rule_id", "rule_version", "artifact_hash"}
    for number, row in enumerate(candidates, 1):
        label = f"candidates:{number}"
        if not isinstance(row, dict) or set(row) != required:
            errors.append(f"{label}: invalid candidate fields")
            continue
        if (not all(isinstance(row[key], str) for key in ("candidate_id", "kind", "state", "reason", "work_unit_id", "artifact_hash"))
                or (row["rule_id"] is not None and not isinstance(row["rule_id"], str))
                or (row["rule_version"] is not None and type(row["rule_version"]) is not int)
                or not re.fullmatch(r"[0-9a-f]{64}", row["artifact_hash"])):
            errors.append(f"{label}: invalid candidate values")
            continue
        if row["candidate_id"] != candidate_id(row):
            errors.append(f"{label}: invalid candidate id")
        if row["candidate_id"] in seen:
            errors.append(f"{label}: duplicate candidate identity")
        seen.add(row["candidate_id"])
        if execution_identity(row) in routed:
            errors.append(f"{label}: conflicting candidate routing")
        routed.add(execution_identity(row))
        execution = executions.get(execution_identity(row))
        if execution is None:
            errors.append(f"{label}: orphaned candidate execution")
        elif execution["outcome"] != "UNRESOLVED":
            errors.append(f"{label}: candidate cites settled execution")
        if row["kind"] not in {"DISCOVER", "REVALIDATE"} or row["state"] != ("SUSPECT" if row["kind"] == "REVALIDATE" else "DISCOVER"):
            errors.append(f"{label}: invalid candidate kind/state")
        if row["kind"] == "REVALIDATE" and row["candidate_id"] not in challenged:
            errors.append(f"{label}: missing RULE_CHALLENGED transition")


def check_protocol_integrity(root: Path) -> list[str]:
    """Report persisted protocol errors without running any project oracle."""
    errors = []
    rules, transitions, executions, candidates = _integrity_files(Path(root), errors)
    recorded, challenged = _integrity_transitions(rules, transitions, candidates, errors)
    by_key = _integrity_executions(executions, recorded, errors)
    _integrity_candidates(candidates, by_key, challenged, errors)
    return errors
