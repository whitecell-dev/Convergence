"""Read structural facts supplied by Ripwire or a saved fixture."""

import json
from pathlib import Path


def read_structural_ir(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("structural IR must be a JSON object")
    # Ripwire's JSON map and the saved CALYX Click fixture are distinct evidence shapes.
    if not ("sigs" in data or {"F", "I", "P"} <= data.keys()):
        raise ValueError("unrecognized structural evidence")
    return data
