"""Select authorized claims at the requested operation boundary."""


def resolve(
    rules: list[dict], framework: str, primitive: str, operation: str
) -> list[dict]:
    query = {"framework": framework, "primitive": primitive, "operation": operation}
    if any(
        rule["state"] == "ACTIVE" and not rule.get("approval_reference")
        for rule in rules
    ):
        raise ValueError("active rule lacks human approval reference")
    return sorted(
        (
            rule
            for rule in rules
            if rule["state"] == "ACTIVE" and rule["scope"] == query
        ),
        key=lambda rule: (rule["id"], rule["version"]),
    )
