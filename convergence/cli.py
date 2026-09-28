"""Small CLI over the shared claim and transition files."""

import argparse
import json
import sys
from pathlib import Path

from .claims import AuthorityStore, STATES, check_protocol_integrity, ensure_layout


def _scope(text):
    if text.lstrip().startswith("{"):
        value = json.loads(text)
        if not isinstance(value, dict):
            raise ValueError("scope JSON must be an object")
        return value
    paths = [part.strip() for part in text.split(",") if part.strip()]
    if not paths:
        raise ValueError("scope needs a path")
    return {"paths": paths}


def main(argv=None):
    parser = argparse.ArgumentParser(prog="convergence")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "add", "authorize", "activate", "challenge", "resolve", "supersede", "retire", "withdraw", "status", "check"):
        sub = commands.add_parser(name)
        sub.add_argument("repo", nargs="?", default=".")
        if name == "add":
            for flag in ("id", "claim", "scope"):
                sub.add_argument(f"--{flag}", required=True)
            sub.add_argument("--evidence-ref", action="append", default=[])
        if name in {"authorize", "activate", "challenge", "resolve", "supersede", "retire", "withdraw"}:
            sub.add_argument("--id", required=True)
            sub.add_argument("--version", required=True, type=int)
        if name in {"authorize", "resolve", "retire", "withdraw", "supersede"}:
            sub.add_argument("--approval-ref", required=True)
        if name == "challenge":
            sub.add_argument("--counterevidence-ref", required=True)
        if name == "resolve":
            sub.add_argument("--resolves", action="append", required=True)
        if name == "supersede":
            sub.add_argument("--superseded-by", type=int, required=True)
    args = parser.parse_args(argv)
    root = Path(args.repo) / ".convergence"
    try:
        if args.command == "init":
            ensure_layout(root)
            print(f"store at {root}")
        elif args.command == "check":
            errors = check_protocol_integrity(root)
            if errors:
                print("\n".join(errors))
                return 1
            print("OK")
        elif args.command == "status":
            store = AuthorityStore(root)
            for state in STATES:
                rows = [r for r in store.rules if r["state"] == state]
                if rows:
                    print(f"{state} ({len(rows)})")
                    for row in rows:
                        print(f"  {row['id']}@{row['version']} {row['claim']}")
            if not store.rules:
                print("no claims recorded yet")
        elif args.command == "add":
            ensure_layout(root)
            store = AuthorityStore(root)
            version = 1 + max((r["version"] for r in store.rules if r["id"] == args.id), default=0)
            store.record_rule({"id": args.id, "version": version, "scope": _scope(args.scope),
                               "claim": args.claim, "evidence_refs": args.evidence_ref})
            print(f"{args.id}@{version} CANDIDATE")
        else:
            store = AuthorityStore(root)
            events = {"authorize": "AUTHORIZED", "activate": "ACTIVE", "challenge": "CHALLENGE",
                      "resolve": "AUTHORIZED", "supersede": "SUPERSEDED", "retire": "RETIRED",
                      "withdraw": "WITHDRAWN"}
            event = {"event": events[args.command], "id": args.id, "version": args.version}
            if hasattr(args, "approval_ref"):
                event["approval_ref"] = args.approval_ref
            if args.command == "challenge":
                event["counterevidence_ref"] = args.counterevidence_ref
            if args.command == "resolve":
                event["resolves"] = args.resolves
            if args.command == "supersede":
                event["superseded_by"] = args.superseded_by
            store.transition(event)
            print(f"{args.id}@{args.version} {store.state(args.id, args.version)}")
        return 0
    except (ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
