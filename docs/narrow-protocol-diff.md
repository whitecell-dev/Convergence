# Narrow protocol diff review

This document describes the change from the previous Convergence implementation to the narrow claim and transition protocol. The previous implementation is preserved on the `experiment` branch.

## What changed

| Area | Previous behavior | Current behavior |
| --- | --- | --- |
| Claim content | One current `rules/<id>.json` file with `constraint`, `oracle`, and one `evidence_reference` | `rules/<id>/v<version>.json` files with `claim` and `evidence_refs`; a hand-written flat file is also accepted |
| Authority | Recording a rule wrote approval and ACTIVE transitions together | `add` creates CANDIDATE; AUTHORIZED and ACTIVE are separate decisions |
| Evidence | `init` created execution and candidate ledgers; integrity checking required them | `init` creates only `rules/` and `transitions.jsonl`; optional evidence files are ignored by protocol checking |
| Challenges | A factory candidate queue drove SUSPECT and resolution | CHALLENGE cites counterevidence directly; restoration must name every open challenge reference |
| Revisions | A new version replaced the current content file | Each version retains its own file; SUPERSEDED links the old version to the next |
| CLI | `add` asked for an oracle and approval and immediately activated the rule | `add`, `authorize`, `activate`, `challenge`, `resolve`, `supersede`, `retire`, and `withdraw` operate on claim transitions |

The main implementation is [claims.py](../convergence/claims.py). It validates the five claim fields, folds transitions into current state, checks version order, rejects incoherent transitions, and prevents two versions of one ID from holding authority at the same point in the log. [cli.py](../convergence/cli.py) exposes those operations. [applicability.py](../convergence/applicability.py) now reads the derived `state` and `approval_ref` fields and excludes SUSPECT claims.

The factory execution, routing, Click oracle, and compilation modules were removed from the `convergence` package. Their old tests and experiment documents were removed with them. [examples/factory/README.md](../examples/factory/README.md) records the adapter boundary without making factory output part of conformance.

The [README](../README.md), [protocol](PROTOCOL.md), [file contract](file-layout.md), and [constitution](CONSTITUTION.md) now describe the shared files and authority rules. Approval references are opaque attribution pointers; repository governance supplies trust. The chosen Git ref determines which committed transition history is authoritative. There is no transition hash chain.

## File contract and lifecycle

A claim file has exactly `id`, `version`, `scope`, `claim`, and `evidence_refs`. Empty `evidence_refs` is valid. State and approval do not live in the claim file. A claim with no transition is CANDIDATE, which allows a hand-written claim plus one AUTHORIZED event to form a valid minimal store.

The fold supports CANDIDATE → AUTHORIZED → ACTIVE, ACTIVE → SUSPECT, restoration through AUTHORIZED → ACTIVE, and retirement or supersession. WITHDRAWN closes a candidate. SUSPECT claims are excluded from new work. Each CHALLENGE carries a `counterevidence_ref`; an AUTHORIZED resolution of the same version must list every outstanding reference in `resolves`. This prevents a later challenge from being cleared by a decision that only addressed an earlier one.

## Compatibility and limits

- This is a breaking on-disk and Python API change. Existing stores using `constraint`, `oracle`, old `RULE_*` events, or factory ledgers need an explicit migration before the new checker or CLI can read them. No automatic migration is included.
- `convergence check` validates file shapes and lifecycle coherence. It does not verify evidence content, authenticate an approver, or inspect branch protections.
- Versioned files retain claim content without Git history, but the protocol relies on the accepted Git history and repository review policy to detect or reject edits to already accepted bytes.
- The checker accepts `rules/<id>.json` for the minimal hand-written case. New CLI writes use `rules/<id>/v<version>.json`.
- A local `convergence` executable was not installed in this workspace. The acceptance case was exercised through the same `convergence.cli:main` entry point named in `pyproject.toml`.

## Verification

`python3 -m unittest discover -s tests -q` passes four tests. They cover the hand-written claim plus AUTHORIZED event with no `evidence/`, the optional evidence directory being ignored, explicit CLI authorization, multiple simultaneous challenges, version retention and supersession, exclusion of SUSPECT claims, and rejection of invalid claim content and transition order. A direct call to the CLI entry point with the supplied hand-written acceptance data returned `OK` and displayed `test@1` as AUTHORIZED. `git diff --check` reports no whitespace errors.
