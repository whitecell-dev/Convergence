"""Lower approved claims onto the saved, immutable Click structural fixture."""

import copy


def compile_rules(rule_set: list[dict], structural_fixture: dict) -> dict:
    """The Click experiment's WR delta leaves the fixture's legacy fields intact."""
    if any(
        rule["state"] == "ACTIVE" and not rule.get("approval_reference")
        for rule in rule_set
    ):
        raise ValueError("active rule lacks human approval reference")
    bundle = copy.deepcopy(structural_fixture)
    active = sorted(
        (rule for rule in rule_set if rule["state"] == "ACTIVE"),
        key=lambda rule: (rule["id"], rule["version"]),
    )
    bundle["WR"] = [
        {
            "id": rule["id"],
            "version": rule["version"],
            "applies_when": rule["scope"],
            "constraint": {**rule["constraint"], "excludes": rule["exclusions"]},
            "instruction": rule["instruction"],
            "oracle": rule["oracle"],
        }
        for rule in active
    ]
    bundle["oracle_specs"] = [
        {
            "id": rule["id"],
            "version": rule["version"],
            "oracle": rule["oracle"],
            "scope": rule["scope"],
            "exclusions": rule["exclusions"],
        }
        for rule in active
    ]
    bundle["generator_constraints"] = [
        {
            "id": rule["id"],
            "version": rule["version"],
            "constraint": rule["constraint"],
            "scope": rule["scope"],
            "exclusions": rule["exclusions"],
            "instruction": rule["instruction"],
        }
        for rule in active
    ]
    return bundle


def parity(bundle: dict, structural_fixture: dict) -> dict[str, bool]:
    """Compare every saved legacy field; WR is an authorized post-fixture delta."""
    return {key: bundle.get(key) == value for key, value in structural_fixture.items()}
