"""Versioned claim content and authority transitions."""

import json
import re
from pathlib import Path

CLAIM_FIELDS = {"id", "version", "scope", "claim", "evidence_refs"}
EVENT_FIELDS = {
    "CANDIDATE": set(), "AUTHORIZED": {"approval_ref"}, "ACTIVE": set(),
    "CHALLENGE": {"counterevidence_ref"}, "SUPERSEDED": {"superseded_by"},
    "RETIRED": set(), "WITHDRAWN": set(),
}
STATES = ("CANDIDATE", "AUTHORIZED", "ACTIVE", "SUSPECT", "SUPERSEDED", "RETIRED", "WITHDRAWN")


def ensure_layout(root):
    root = Path(root)
    (root / "rules").mkdir(parents=True, exist_ok=True)
    (root / "transitions.jsonl").touch(exist_ok=True)


def read_jsonl(path):
    path = Path(path)
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
    with Path(path).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, sort_keys=True) + "\n")


def validate_rule(rule):
    if not isinstance(rule, dict) or set(rule) != CLAIM_FIELDS:
        raise ValueError("claim needs exactly id, version, scope, claim, evidence_refs")
    if not isinstance(rule["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", rule["id"]):
        raise ValueError("invalid claim id")
    if type(rule["version"]) is not int or rule["version"] < 1:
        raise ValueError("version must be a positive integer")
    if not isinstance(rule["scope"], dict):
        raise ValueError("scope must be an object")
    if not isinstance(rule["claim"], str) or not rule["claim"].strip():
        raise ValueError("claim must be nonblank text")
    if not isinstance(rule["evidence_refs"], list) or not all(
        isinstance(ref, str) and ref.strip() for ref in rule["evidence_refs"]
    ):
        raise ValueError("evidence_refs must be a list of nonblank strings")


def _load_claims(root, errors):
    claims = {}
    paths = sorted((root / "rules").rglob("*.json"))
    for path in paths:
        try:
            claim = json.loads(path.read_text(encoding="utf-8"))
            validate_rule(claim)
            flat = path.parent == root / "rules"
            expected = (root / "rules" / f"{claim['id']}.json" if flat else
                        root / "rules" / claim["id"] / f"v{claim['version']}.json")
            if path != expected:
                raise ValueError("claim id/version differs from path")
            key = claim["id"], claim["version"]
            if key in claims:
                raise ValueError("duplicate claim version")
            claims[key] = claim
        except (ValueError, OSError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return claims


def _fold(claims, transitions, errors):
    states, approvals, pending = {}, {}, {}
    versions = {}
    for claim_id, version in sorted(claims):
        if version != versions.get(claim_id, 0) + 1:
            errors.append(f"{claim_id}@{version}: versions must start at 1 and advance by one")
        versions[claim_id] = version
    for number, event in enumerate(transitions, 1):
        label = f"transitions.jsonl:{number}"
        if not isinstance(event, dict) or not isinstance(event.get("event"), str) or event["event"] not in EVENT_FIELDS:
            errors.append(f"{label}: unknown transition event")
            continue
        kind = event["event"]
        required = {"event", "id", "version"} | EVENT_FIELDS[kind]
        allowed = required | {"timestamp", "actor"}
        if kind == "AUTHORIZED":
            allowed.add("resolves")
        if kind in {"SUPERSEDED", "RETIRED", "WITHDRAWN"}:
            allowed.add("approval_ref")
        if (not required <= set(event) or set(event) - allowed
                or not isinstance(event["id"], str) or type(event["version"]) is not int
                or ("timestamp" in event and not isinstance(event["timestamp"], str))
                or ("actor" in event and not isinstance(event["actor"], str))
                or ("approval_ref" in event and (not isinstance(event["approval_ref"], str) or not event["approval_ref"].strip()))):
            errors.append(f"{label}: invalid transition fields")
            continue
        key = event["id"], event["version"]
        if key not in claims:
            errors.append(f"{label}: unknown claim version")
            continue
        previous = states.get(key, "CANDIDATE")
        if kind == "CANDIDATE":
            valid, state = key not in states, "CANDIDATE"
        elif kind == "AUTHORIZED":
            ref = event["approval_ref"]
            valid = previous in {"CANDIDATE", "SUSPECT"} and isinstance(ref, str) and bool(ref.strip())
            resolutions = event.get("resolves", [])
            if previous == "SUSPECT":
                valid = valid and isinstance(resolutions, list) and all(isinstance(r, str) for r in resolutions) and set(resolutions) == pending.get(key, set()) and len(resolutions) == len(set(resolutions))
            else:
                valid = valid and "resolves" not in event
            state = "AUTHORIZED"
            if valid:
                approvals[key] = ref
                pending[key] = set()
        elif kind == "ACTIVE":
            valid, state = previous == "AUTHORIZED", "ACTIVE"
        elif kind == "CHALLENGE":
            ref = event["counterevidence_ref"]
            valid = previous in {"ACTIVE", "SUSPECT"} and isinstance(ref, str) and bool(ref.strip()) and ref not in pending.get(key, set())
            state = "SUSPECT"
            if valid:
                pending.setdefault(key, set()).add(ref)
        elif kind == "SUPERSEDED":
            next_version = event["superseded_by"]
            valid = previous in {"AUTHORIZED", "ACTIVE", "SUSPECT"} and type(next_version) is int and next_version == key[1] + 1 and (key[0], next_version) in claims
            state = "SUPERSEDED"
        elif kind == "RETIRED":
            valid, state = previous in {"AUTHORIZED", "ACTIVE", "SUSPECT"}, "RETIRED"
        else:
            valid, state = previous == "CANDIDATE", "WITHDRAWN"
        blocker = None
        if valid and state in {"AUTHORIZED", "ACTIVE", "SUSPECT"}:
            blocker = next(((other_id, other_version) for (other_id, other_version), other_state in states.items()
                            if other_id == key[0] and other_version != key[1]
                            and other_state in {"AUTHORIZED", "ACTIVE", "SUSPECT"}), None)
            valid = blocker is None
        if valid:
            states[key] = state
        else:
            reason = f"; {blocker[0]}@{blocker[1]} still holds authority" if blocker else ""
            errors.append(f"{label}: incoherent lifecycle transition {kind} "
                          f"{key[0]}@{key[1]} from {previous}{reason}")
    return states, approvals, pending


def check_protocol_integrity(root):
    """Check only the shared file contract, ignoring optional adapters."""
    root = Path(root)
    errors = []
    for relative in ("rules", "transitions.jsonl"):
        path = root / relative
        if not (path.is_dir() if relative == "rules" else path.is_file()):
            errors.append(f"missing protocol path: {relative}")
    claims = _load_claims(root, errors)
    try:
        transitions = read_jsonl(root / "transitions.jsonl")
    except ValueError as exc:
        errors.append(str(exc))
        transitions = []
    _fold(claims, transitions, errors)
    return errors


class AuthorityStore:
    def __init__(self, root):
        self.root = Path(root)
        self.transition_path = self.root / "transitions.jsonl"
        self.reload()

    def reload(self):
        errors = check_protocol_integrity(self.root)
        if errors:
            raise ValueError("; ".join(errors))
        claims = _load_claims(self.root, [])
        self.states, self.approvals, self.pending = _fold(claims, read_jsonl(self.transition_path), [])
        self.rules = [{**claim, "state": self.states.get(key, "CANDIDATE"),
                       "approval_ref": self.approvals.get(key)}
                      for key, claim in sorted(claims.items())]
        return self.rules

    def state(self, claim_id, version):
        return next((r["state"] for r in self.rules
                     if r["id"] == claim_id and r["version"] == version), None)

    def status(self):
        return {"rules": self.rules, "counts": {state: sum(
            r["state"] == state for r in self.rules) for state in STATES}}

    def record_rule(self, rule):
        validate_rule(rule)
        if rule["version"] != 1 + max((r["version"] for r in self.rules if r["id"] == rule["id"]), default=0):
            raise ValueError("version must start at 1 and advance by one")
        ensure_layout(self.root)
        path = self.root / "rules" / rule["id"] / f"v{rule['version']}.json"
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps(rule, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        append_jsonl(self.transition_path, {"event": "CANDIDATE", "id": rule["id"], "version": rule["version"]})
        self.reload()
        return rule

    def transition(self, event):
        errors = []
        claims = _load_claims(self.root, errors)
        _fold(claims, [*read_jsonl(self.transition_path), event], errors)
        if errors:
            raise ValueError("; ".join(errors))
        append_jsonl(self.transition_path, event)
        self.reload()
