"""Select authorized claims at the requested operation boundary."""


def resolve(rules: list[dict], query: dict, matcher=None) -> list[dict]:
    if matcher is None:
        if not isinstance(query, dict):
            raise ValueError("default scope query must be an object")
        matcher = lambda scope, supplied: all(key in scope and scope[key] == value for key, value in supplied.items())
    if any(
        rule["state"] == "ACTIVE" and not rule.get("approval_ref")
        for rule in rules
    ):
        raise ValueError("active rule lacks human approval reference")
    return sorted(
        (
            rule
            for rule in rules
            if rule["state"] == "ACTIVE" and matcher(rule["scope"], query)
        ),
        key=lambda rule: (rule["id"], rule["version"]),
    )
