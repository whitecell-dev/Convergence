"""Append immutable WorkUnit evidence with three distinct outcomes."""

import hashlib
from pathlib import Path

from .claims import AuthorityStore, append_jsonl, ensure_layout, execution_identity, read_jsonl


def record_execution(
    root: Path,
    work_unit_id: str,
    artifact: Path,
    result: dict,
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
    if result["oracle_ran"] != (result["oracle_result"] in {"pass", "violated"}):
        raise ValueError("oracle_ran contradicts oracle_result")
    root = Path(root)
    ensure_layout(root)
    ledger = root / "evidence/executions.jsonl"
    identity = (work_unit_id, result["rule_id"], result["rule_version"], digest)
    # ponytail: linear ledger scan is enough for the small, single-writer v0 store.
    for existing in read_jsonl(ledger):
        if execution_identity(existing) == identity:
            return existing
    approved = next((rule for rule in AuthorityStore(root).rules if
        rule["id"] == result["rule_id"]
        and rule["version"] == result["rule_version"]
        and rule["authority_state"] == "ACTIVE"
        and rule.get("approval_reference")
    ), None)
    if result["rule_id"] is not None and approved is None:
        raise ValueError("execution cites no active approved rule")
    if approved is not None and approved["oracle"] is None and (
        result["oracle_ran"] or result["oracle_result"] in {"pass", "violated"}
    ):
        raise ValueError("rule has no oracle; execution cannot be proven or violated")
    if result["applicable"] and result["rule_id"] is None:
        raise ValueError("applicable result requires an approved rule")
    if result["oracle_result"] in {"pass", "violated"} and not result["applicable"]:
        raise ValueError("proof or violation requires an applicable rule")
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
        "artifact_hash": digest,
        "applicable": result["applicable"],
        "oracle_ran": result["oracle_ran"],
        "oracle_result": result["oracle_result"],
        "outcome": outcome,
    }
    append_jsonl(ledger, record)
    return record
