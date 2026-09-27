"""Package approved rules with supplied structural evidence for consumers."""

import copy


def compile_rules(rule_set: list[dict], structural_fixture: dict) -> dict:
    """Preserve structural evidence and include only active approved rules."""
    if any(
        rule["authority_state"] == "ACTIVE" and not rule.get("approval_reference")
        for rule in rule_set
    ):
        raise ValueError("active rule lacks human approval reference")
    active = sorted(
        (copy.deepcopy(rule) for rule in rule_set if rule["authority_state"] == "ACTIVE"),
        key=lambda rule: (rule["id"], rule["version"]),
    )
    return {"structural_ir": copy.deepcopy(structural_fixture), "rules": active}


def parity(bundle: dict, structural_fixture: dict) -> bool:
    """Check that rule compilation preserved the supplied structural evidence."""
    return bundle["structural_ir"] == structural_fixture
