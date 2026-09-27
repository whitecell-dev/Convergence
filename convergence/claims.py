"""Approval-gated, versioned claims. Investigation and approval happen elsewhere."""

import json
import os
import tempfile
from pathlib import Path

STATES = {"OBSERVED", "CANDIDATE", "STABILIZED", "ACTIVE", "SUSPECT", "RETIRED"}
FIELDS = {
    "id",
    "version",
    "scope",
    "exclusions",
    "constraint",
    "instruction",
    "oracle",
    "state",
}


class AuthorityStore:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.path = self.directory / "rules.json"
        self.rules = json.loads(self.path.read_text()) if self.path.exists() else []

    def record_rule(self, rule: dict, approval_reference: str) -> dict:
        if (
            not approval_reference
            or set(rule) != FIELDS
            or rule["state"] not in STATES
            or rule["state"] != "ACTIVE"
        ):
            raise ValueError(
                "an ACTIVE rule and explicit human approval reference are required"
            )
        if not isinstance(rule["version"], int) or rule["version"] < 1:
            raise ValueError("rule version must be a positive integer")
        if not all(rule[key] for key in FIELDS - {"exclusions"}):
            raise ValueError("rule has an empty required field")
        if set(rule["scope"]) != {"framework", "primitive", "operation"}:
            raise ValueError(
                "rule scope must identify framework, primitive, and operation"
            )
        prior = [old for old in self.rules if old["id"] == rule["id"]]
        if not prior and rule["version"] != 1:
            raise ValueError("first authorized version must be 1")
        if prior and (
            rule["version"] != max(old["version"] for old in prior) + 1
            or any(
                old["state"] == "ACTIVE" and old["scope"] != rule["scope"]
                for old in prior
            )
        ):
            raise ValueError("revision must advance the version and retain its scope")
        if any(
            old["id"] == rule["id"] and old["version"] == rule["version"]
            for old in prior
        ):
            raise ValueError("duplicate rule version")
        # Approval is an external human decision; this core only requires and records its reference.
        self.directory.mkdir(parents=True, exist_ok=True)
        updated = json.loads(json.dumps(self.rules))
        for old in updated:
            if old["id"] != rule["id"]:
                continue
            if old["state"] == "ACTIVE":
                old["state"] = "RETIRED"
        saved = json.loads(json.dumps(rule))
        saved["approval_reference"] = approval_reference
        updated.append(saved)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.directory, prefix=".rules-", delete=False
        ) as stream:
            json.dump(updated, stream, sort_keys=True, indent=2)
            stream.write("\n")
            temporary = stream.name
        os.replace(temporary, self.path)
        self.rules = updated
        return saved
