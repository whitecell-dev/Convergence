# Agent guide

How to use the `convergence` CLI. This is operational guidance; [PROTOCOL.md](PROTOCOL.md) is normative and [file-layout.md](file-layout.md) is the field contract.

## The model in 30 seconds

Two kinds of file under `.convergence/`:

- `rules/<id>/v<version>.json` — immutable claim content. Exactly five fields: `id`, `version`, `scope`, `claim`, `evidence_refs`.
- `transitions.jsonl` — append-only authority events, one JSON object per line.

**State is the fold of `transitions.jsonl`, never stored in a claim file.** A claim file with no transition is `CANDIDATE`.

Only `ACTIVE` permits reliance. `SUSPECT` means the claim is not authoritative for new work. Authority comes from an explicit human decision citing an `approval_ref` — never from evidence, tests, CI, or your own judgment.

## Ordering rule (read this twice)

> **Only one version of an ID may hold authority at a time. `AUTHORIZED` counts as authority, not just `ACTIVE`.**
>
> To revise: `add` the new version → `supersede`/`retire` the old one → **then** `authorize` the new one → `activate` it.
>
> Reversing those two middle steps fails with `incoherent lifecycle transition`.

```text
wrong: add v2 -> authorize v2 -> supersede v1     # v1 is still ACTIVE, v2 cannot be AUTHORIZED
right: add v2 -> supersede v1 -> authorize v2 -> activate v2
```

## Commands

Every command takes an optional trailing repository path, default `.`. All exit `0` on success, `1` on a rejected operation, `2` on a bad flag.

| Command | Required flags | Effect |
| --- | --- | --- |
| `init` | — | Creates `rules/` and `transitions.jsonl`. Nothing else. |
| `add` | `--id --claim --scope` (`--evidence-ref` repeatable) | Writes the next version as `CANDIDATE`. |
| `authorize` | `--id --version --approval-ref` | Records the human decision. Does **not** permit reliance. |
| `activate` | `--id --version` | Permits reliance. Requires `AUTHORIZED`. |
| `challenge` | `--id --version --counterevidence-ref` | `ACTIVE` → `SUSPECT`. Requires `ACTIVE` or `SUSPECT`. |
| `resolve` | `--id --version --approval-ref --resolves` (repeatable) | `SUSPECT` → `AUTHORIZED`. Must list **every** open challenge ref. |
| `supersede` | `--id --version --superseded-by --approval-ref` | Ends the old version. Next version's file must already exist. |
| `retire` | `--id --version --approval-ref` | Ends an authorized or active version. |
| `withdraw` | `--id --version --approval-ref` | Ends a `CANDIDATE`. |
| `status` | — | Groups every claim by state. Read-only. |
| `check` | — | Validates the file contract. Read-only. `OK` or a list of errors. |

`--scope` takes comma-separated paths, or a JSON object if it starts with `{`:

```sh
convergence add --id a.b --claim "..." --scope "src/api/,src/db/"     # -> {"paths": ["src/api/", "src/db/"]}
convergence add --id a.b --claim "..." --scope '{"framework": "click"}'
```

## Flows

New claim:

```sh
convergence add --id api.user-id-format --claim "User IDs are UUIDv7." \
  --scope "src/api/" --evidence-ref "git:HEAD:tests/test_user_ids.py"
convergence authorize --id api.user-id-format --version 1 --approval-ref PR-381
convergence activate  --id api.user-id-format --version 1
convergence check
```

Revision (note the order — `supersede` before `authorize`):

```sh
convergence add --id api.user-id-format --claim "User IDs are UUIDv7, lowercase." \
  --scope "src/api/" --evidence-ref "git:HEAD:tests/test_user_ids.py"   # writes v2 CANDIDATE
convergence supersede --id api.user-id-format --version 1 --superseded-by 2 --approval-ref PR-4
convergence authorize --id api.user-id-format --version 2 --approval-ref PR-4
convergence activate  --id api.user-id-format --version 2
```

Challenge and restore the same version:

```sh
convergence challenge --id api.user-id-format --version 1 --counterevidence-ref "git:abc123:prod/incident-42.md"
convergence status                                    # now SUSPECT: stop relying on it
convergence resolve  --id api.user-id-format --version 1 --approval-ref PR-3 \
  --resolves "git:abc123:prod/incident-42.md"        # must repeat --resolves for every open challenge
convergence activate --id api.user-id-format --version 1
```

## Traps

| Symptom | Cause |
| --- | --- |
| `... still holds authority` | You authorized a new version before superseding or retiring the old one. |
| `unknown claim version` | The claim file does not exist yet. `add` it, or hand-write it. |
| `incoherent ... ACTIVE t@1 from CANDIDATE` | Skipped `authorize`. `activate` requires `AUTHORIZED`. |
| `incoherent ... AUTHORIZED t@1 from CANDIDATE` | Used `resolve` on a claim that is not `SUSPECT`. Use `authorize`. |
| `incoherent ... CHALLENGE t@1 from AUTHORIZED` | You challenged before activating. Only `ACTIVE` or `SUSPECT` can be challenged. |
| `incoherent ... SUPERSEDED t@1 from AUTHORIZED` | `superseded-by` names a version whose file does not exist yet. |
| `duplicate claim version` | Two files describe the same `id`@`version`. |
| `claim needs exactly id, version, scope, claim, evidence_refs` | Extra or missing field, or `evidence_refs` not a list of nonblank strings. |

More, stated flatly:

- `add` picks the version for you. There is no `--version` flag on `add`; passing one is a usage error.
- `add` writes the `CANDIDATE` event for you. A hand-written claim file needs no `CANDIDATE` event.
- `add` writes the versioned path `rules/<id>/v<n>.json`. A hand-written flat `rules/<id>.json` is also accepted, but do not use both paths for the same `id`@`version`.
- Versions start at 1 and advance by one. A gap is a `versions must start at 1 and advance by one` error, not an auto-fill.
- Claim content is immutable per version. To change the text, create the next version.
- `evidence_refs: []` is valid and means none recorded. Prefer `git:<commit>:<path>` over a bare path; bare paths drift.
- Ids match `[A-Za-z0-9][A-Za-z0-9._-]*` and are used as directory names.
- `resolve` must list **all** open `counterevidence_ref` values. Resolving only some leaves the claim `SUSPECT`. Get the full set from `convergence status` plus the `CHALLENGE` lines in `transitions.jsonl`.
- `--approval-ref` is any nonblank opaque string: `PR-381`, `MR!12`, `email:...`, `commit:...`.
- `check` validates only `rules/` and `transitions.jsonl`. It ignores `evidence/` and any other file.
- `check` and `status` never write. Every other command appends.

## Consuming claims

Before relying on a project claim, run `convergence status` and use only `ACTIVE` entries. Skip `SUSPECT` entirely for new work. In Python, `convergence.applicability.resolve(rules, query)` returns exactly the `ACTIVE` claims whose scope matches, and raises if an `ACTIVE` claim lacks an approval reference.

## What Convergence does not do

It does not discover claims, evaluate or fetch evidence, run tests, authenticate an approver, enforce branch protection, or instruct you. `approval_ref` is attribution, not authentication; repository governance supplies trust. It is a place to record what people already decided, not a way to reach that decision.
