"""Route unresolved evidence into append-only candidate queues."""

from pathlib import Path

from .claims import AuthorityStore, append_jsonl, candidate_id, execution_identity, read_jsonl


def classify(record: dict, root: Path) -> str | dict:
    if record["outcome"] != "UNRESOLVED":
        return record["outcome"]
    root = Path(root)
    for filename in ("discover_candidates.jsonl", "revalidate_candidates.jsonl"):
        for existing in read_jsonl(root / "evidence" / filename):
            if execution_identity(existing) == execution_identity(record):
                return existing
    store = AuthorityStore(root)
    rule = next((item for item in store.rules if item["id"] == record["rule_id"] and item["version"] == record["rule_version"]), None)
    challenged = bool(record["applicable"] and not record["oracle_ran"] and rule and rule["oracle"] is not None)
    candidate = {
        "kind": "REVALIDATE" if challenged else "DISCOVER",
        "state": "SUSPECT" if challenged else "DISCOVER",
        "work_unit_id": record["work_unit_id"],
        "rule_id": record["rule_id"],
        "rule_version": record["rule_version"],
        "artifact_hash": record["artifact_hash"],
        "reason": "declared rule has no available oracle" if challenged else "no applicable proof",
    }
    candidate["candidate_id"] = candidate_id(candidate)
    filename = "revalidate_candidates.jsonl" if challenged else "discover_candidates.jsonl"
    path = root / "evidence" / filename
    # ponytail: linear scan assumes a single writer; concurrent agents need a Git lock.
    for existing in read_jsonl(path):
        if existing["candidate_id"] == candidate["candidate_id"]:
            return existing
    append_jsonl(path, candidate)
    if challenged:
        append_jsonl(store.transition_path, {"event": "RULE_CHALLENGED", "rule_id": record["rule_id"],
                                            "rule_version": record["rule_version"], "candidate_id": candidate["candidate_id"]})
    return candidate
