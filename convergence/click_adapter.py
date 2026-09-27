"""The narrow Click source oracle proven by the archived option experiments."""

import ast
import re
from pathlib import Path


def _decorator(node: ast.expr) -> str | None:
    target = node.func if isinstance(node, ast.Call) else node
    if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "click":
        return target.attr
    return None


def evaluate(artifact: Path, rule: dict | None) -> dict:
    """Return an oracle observation; the authority core decides what it means."""
    result = {"rule_id": rule["id"] if rule else None,
              "rule_version": rule["version"] if rule else None,
              "applicable": False, "oracle_ran": False,
              "oracle_result": "not_applicable"}
    if rule is None:
        return result
    if rule["oracle"] != "click_validator:option.callback_keyword_binding":
        raise ValueError("unsupported Click oracle")
    tree = ast.parse(Path(artifact).read_text(encoding="utf-8"), filename=str(artifact))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or len(node.decorator_list) != 2:
            continue
        command, option = node.decorator_list
        if [_decorator(command), _decorator(option)] != ["command", "option"]:
            continue
        if not (isinstance(command, ast.Call) and not command.args and not command.keywords and
                isinstance(option, ast.Call) and len(option.args) == 1 and
                isinstance(option.args[0], ast.Constant) and isinstance(option.args[0].value, str) and
                re.fullmatch(r"--[A-Za-z][A-Za-z0-9-]*", option.args[0].value) and
                not any(keyword.arg in {"cls", None} for keyword in option.keywords) and
                len(node.args.args) == 1 and not node.args.posonlyargs and not node.args.kwonlyargs and
                node.args.vararg is None and node.args.kwarg is None):
            continue
        exposure = next((kw for kw in option.keywords if kw.arg == "expose_value"), None)
        suppressed = (exposure is not None and isinstance(exposure.value, ast.Constant)
                      and exposure.value.value is False)
        if suppressed and "expose_value=False" in rule["exclusions"]:
            return result
        result["applicable"] = True
        if suppressed or exposure is not None:
            result["oracle_result"] = "unavailable"
            return result
        result["oracle_ran"] = True
        name = option.args[0].value[2:].replace("-", "_").lower()
        result["oracle_result"] = "pass" if name == node.args.args[0].arg else "violated"
        return result
    return result
