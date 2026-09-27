"""Append immutable WorkUnit evidence with three distinct outcomes."""

import hashlib
import json
from pathlib import Path


def record_execution(
    directory: Path,
    work_unit_id: str,
    artifact: Path,
    result: dict,
    authorized_rules: list[dict],
    expected_hash: str | None = None,
) -> dict:
    artifact = Path(artifact)
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if expected_hash is not None and digest != expected_hash:
        raise ValueError("artifact hash differs from saved evidence")
    if result["oracle_result"] not in {
        "pass",
        "violated",
        "unavailable",
        "not_applicable",
    }:
        raise ValueError("unknown oracle result")
    if result["rule_id"] is not None and not any(
        rule["id"] == result["rule_id"]
        and rule["version"] == result["rule_version"]
        and rule["state"] == "ACTIVE"
        and rule.get("approval_reference")
        for rule in authorized_rules
    ):
        raise ValueError("execution cites no active approved rule")
    if result["applicable"] and result["rule_id"] is None:
        raise ValueError("applicable result requires an approved rule")
    if result["oracle_result"] == "pass" and not (
        result["applicable"] and result["oracle_ran"]
    ):
        raise ValueError("proof requires an applicable oracle that ran")
    if result["oracle_result"] == "violated" and not (
        result["applicable"] and result["oracle_ran"]
    ):
        raise ValueError("violation requires an applicable oracle that ran")
    if result["oracle_result"] == "unavailable" and not result["applicable"]:
        raise ValueError("an unavailable oracle must have a declared applicable rule")
    outcome = (
        "VIOLATED"
        if result["oracle_result"] == "violated"
        else "PROVEN"
        if result["oracle_result"] == "pass"
        else "UNRESOLVED"
    )
    record = {
        "work_unit_id": work_unit_id,
        "rule_id": result["rule_id"],
        "rule_version": result["rule_version"],
        "artifact": str(artifact),
        "artifact_hash": digest,
        "applicable": result["applicable"],
        "oracle_ran": result["oracle_ran"],
        "oracle_result": result["oracle_result"],
        "outcome": outcome,
    }
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / "executions.jsonl").open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, sort_keys=True) + "\n")
    return record
