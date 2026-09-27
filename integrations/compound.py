"""Turn a captured CE note into a DISCOVER candidate, without authority writes."""

import hashlib
import json
from pathlib import Path


def capture_candidate(note_path: Path, execution: dict, candidate_path: Path) -> dict:
    note_path = Path(note_path)
    note = note_path.read_bytes()
    if execution["outcome"].upper() != "UNRESOLVED" or not note.strip():
        raise ValueError("a nonempty note and unresolved execution are required")
    candidate = {
        "kind": "DISCOVER",
        "state": "DISCOVER",
        "reason": f"captured note {note_path} sha256:{hashlib.sha256(note).hexdigest()}",
        "work_unit_id": execution["work_unit_id"],
        "artifact_hash": execution["artifact_hash"],
        "challenged_rule_id": None,
        "challenged_rule_version": None,
    }
    destination = Path(candidate_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(candidate, sort_keys=True) + "\n")
    return candidate
