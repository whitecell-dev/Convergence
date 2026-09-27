"""Command line wrapper over the v0 protocol. No config file, no daemon."""

import argparse
import json
import sys
from pathlib import Path

from .claims import AuthorityStore, check_protocol_integrity, ensure_layout

STORE = ".convergence"


def _scope(text: str) -> dict:
    """Accept a JSON object, a single path, or comma-separated paths."""
    if text.lstrip().startswith("{"):
        scope = json.loads(text)
        if not isinstance(scope, dict):
            raise ValueError("scope JSON must be an object")
        return scope
    paths = [part.strip() for part in text.split(",") if part.strip()]
    if not paths:
        raise ValueError("scope needs at least one path")
    return {"paths": paths}


def _ask(label: str) -> str:
    return input(f"{label}: ").strip()


def _cmd_init(args) -> int:
    root = Path(STORE)
    before = set(root.rglob("*")) if root.is_dir() else set()
    ensure_layout(root)
    created = sorted(str(path) for path in root.rglob("*") if path not in before)
    for path in created:
        print(f"created {path}")
    print("already present" if not created else f"store at {root}/")
    print()
    print("next: convergence add      # record one approved rule")
    print("      convergence status    # see what is recorded")
    return 0


def _cmd_add(args) -> int:
    # Any required flag selects non-interactive mode; with none, prompt for all six fields.
    if any((args.id, args.constraint, args.scope, args.approval)):
        fields = (
            args.id,
            args.constraint,
            args.scope,
            args.evidence,
            args.oracle,
            args.approval,
        )
    else:
        fields = (
            _ask("Rule ID"),
            _ask("What may the project rely on? (constraint)"),
            _ask(
                "Where does this apply? (path, comma-separated paths, or JSON object)"
            ),
            _ask("Evidence reference (optional)"),
            _ask("Oracle reference (optional, may be left blank)"),
            _ask("Approval reference (required)"),
        )
    rule_id, constraint, scope, evidence, oracle, approval = fields
    store = AuthorityStore(Path(STORE))
    prior = next((row for row in store.rules if row["id"] == rule_id), None)
    rule = {
        "id": rule_id,
        "version": prior["version"] + 1 if prior else 1,
        "scope": _scope(scope),
        "constraint": constraint,
        "oracle": oracle or None,
        "evidence_reference": evidence or None,
        "authority_state": "ACTIVE",
    }
    saved = store.record_rule(rule, approval)
    print(
        f"{saved['id']} v{saved['version']} {saved['authority_state']} -> {STORE}/rules/{rule_id}.json"
    )
    available = saved["oracle"] is not None
    print(
        f"mechanical verification: {'declared ' + saved['oracle'] if available else 'unavailable (no oracle reference)'}"
    )
    return 0


def _cmd_status(args) -> int:
    store = AuthorityStore(Path(STORE))
    report = store.status()
    if not report["rules"]:
        print("no rules recorded yet")
        print(
            "next: convergence add --id <id> --constraint <text> --scope <scope> --approval <ref>"
        )
        return 0
    scopes = {row["id"]: row["scope"] for row in store.rules}
    challenges = {
        (c["rule_id"], c["rule_version"]): c
        for c in report["open_candidates"]
        if c["kind"] == "REVALIDATE"
    }
    for state in ("ACTIVE", "SUSPECT", "RETIRED"):
        group = [row for row in report["rules"] if row["authority_state"] == state]
        if not group:
            continue
        print(f"{state} ({len(group)})")
        for row in group:
            line = (
                f"  {row['id']} v{row['version']}  "
                f"scope={json.dumps(scopes.get(row['id'], {}), sort_keys=True)}  "
                f"verification={row['verification']}"
            )
            challenger = challenges.get((row["id"], row["version"]))
            if challenger:
                line += f"  challenged by candidate {challenger['candidate_id'][:12]}"
            print(line)
    open_candidates = report["open_candidates"]
    if open_candidates:
        print(f"open candidates ({len(open_candidates)})")
        for row in open_candidates:
            print(
                f"  {row['candidate_id'][:12]}  {row['kind']}  {row['work_unit_id']}  {row['reason']}"
            )
    counts = report["counts"]
    print(
        f"counts: ACTIVE={counts['ACTIVE']} SUSPECT={counts['SUSPECT']} RETIRED={counts['RETIRED']} "
        f"open_candidates={len(open_candidates)}"
    )
    return 0


def _cmd_check(args) -> int:
    errors = check_protocol_integrity(Path(STORE))
    if not errors:
        print("OK")
        return 0
    for error in errors:
        print(error)
    return 1


def _parser() -> argparse.ArgumentParser:
    formatter = argparse.RawDescriptionHelpFormatter
    parser = argparse.ArgumentParser(
        prog="convergence",
        description="Record and inspect approved claims.",
        formatter_class=formatter,
    )
    commands = parser.add_subparsers(dest="command", required=True)

    def add_command(name, brief, description, run):
        sub = commands.add_parser(
            name, help=brief, description=description, formatter_class=formatter
        )
        sub.set_defaults(run=run)
        return sub

    add_command(
        "init",
        "create the store here",
        "Create .convergence/ in the current directory. Idempotent.\n\n"
        "  convergence init",
        _cmd_init,
    )

    add = add_command(
        "add",
        "record one approved rule",
        "Record one approved rule. Prompts for any field not given as a flag.\n"
        "Flags: --id --constraint --scope --approval, plus optional --evidence --oracle.\n\n"
        "  convergence add --id api.user-id --constraint 'User IDs are UUIDv7.' \\\n"
        '      --scope \'{"paths":["src/api/"]}\' --approval PR-381',
        _cmd_add,
    )
    for flag in ("id", "constraint", "scope", "evidence", "oracle", "approval"):
        add.add_argument(f"--{flag}", metavar=flag.upper(), help=argparse.SUPPRESS)

    add_command(
        "status",
        "show rules, candidates, counts",
        "Show rules by authority state, open candidates, and counts.\n\n"
        "  convergence status",
        _cmd_status,
    )

    add_command(
        "check",
        "check the store for protocol errors",
        "Check the persisted store for protocol errors. Runs no oracles.\n\n"
        "  convergence check",
        _cmd_check,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return args.run(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
