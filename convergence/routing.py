"""Route unresolved evidence into append-only candidate queues, never rules."""

import json
from pathlib import Path


def classify(record: dict, directory: Path) -> str | dict:
    if record["outcome"] != "UNRESOLVED":
        return record["outcome"]
    drift = record["applicable"] and not record["oracle_ran"]
    candidate = {
        "kind": "REVALIDATE" if drift else "DISCOVER",
        "state": "SUSPECT" if drift else "DISCOVER",
        "work_unit_id": record["work_unit_id"],
        "rule_id": record["rule_id"],
        "rule_version": record["rule_version"],
        "artifact": record["artifact"],
        "artifact_hash": record["artifact_hash"],
        "reason": "declared rule has no available oracle"
        if drift
        else "no applicable proof",
    }
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    filename = (
        "revalidation_candidates.jsonl" if drift else "discovery_candidates.jsonl"
    )
    with (directory / filename).open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(candidate, sort_keys=True) + "\n")
    return candidate
