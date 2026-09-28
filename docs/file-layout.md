# Convergence file contract

The required directory is `.convergence/` with `rules/` and `transitions.jsonl`. Every other file is optional and outside protocol conformance. For each proposed core file ask: **Would two independent implementations need it to agree on the current authorized claim?**

## Claim files

The durable path is `rules/<id>/v<version>.json`. The shorthand `rules/<id>.json` is accepted for hand-written stores; it represents only its stated version. Do not use both paths for the same ID/version. Versions start at 1 and advance by one. Versioned files allow reconstruction without Git history.

Each file has exactly these fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable ID using letters, digits, periods, underscores, or hyphens. |
| `version` | Positive integer for this exact claim and scope. |
| `scope` | JSON object describing where the claim applies. Consumers interpret its keys. |
| `claim` | Nonblank statement the project may rely on. |
| `evidence_refs` | List of nonblank pointers; `[]` explicitly means none recorded. |

Pin evidence when attribution matters: `git:<commit>:<path>` or `artifact:<id>:<digest>`. Bare paths and lines can drift. Convergence stores pointers, not evidence content.

## Transitions

One JSON object per line, in order. Every event has `event`, `id`, and `version`. Optional `timestamp` and `actor` strings are metadata. State is the fold of events, never stored in claim content. A claim file with no transition is CANDIDATE.

| Event | Additional fields | Effect |
| --- | --- | --- |
| `CANDIDATE` | none | Explicitly records a proposed version. |
| `AUTHORIZED` | `approval_ref`; `resolves` when resolving challenges | Records a human decision; state AUTHORIZED. |
| `ACTIVE` | none | Permits reliance after AUTHORIZED. |
| `CHALLENGE` | `counterevidence_ref` | Makes ACTIVE or SUSPECT claim SUSPECT. |
| `SUPERSEDED` | `superseded_by` | Links an older version to the next version. |
| `RETIRED` | none | Ends an authorized or active version. |
| `WITHDRAWN` | none | Ends a candidate version. |

`approval_ref` is any nonblank opaque string: `PR-381`, `MR!12`, `email:...`, and `commit:...` are examples. It is attribution, not proof of identity. Repository governance supplies trust. `SUPERSEDED`, `RETIRED`, and `WITHDRAWN` may also carry an approval reference.

A challenge reference identifies one open challenge for that version. More distinct challenges may arrive while SUSPECT. Restoring the same version requires an `AUTHORIZED` event whose `resolves` array lists **every** open `counterevidence_ref`. Then `ACTIVE` restores reliance. A missing reference leaves the claim SUSPECT. To revise, create the next version as CANDIDATE, then SUPERSEDE or RETIRE the old version before authorizing the new one. `REVISED` is a relationship, not a state.

`SUSPECT` means **do not treat the claim as authoritative for new work**. `AUTHORIZED` records review but does not permit reliance until `ACTIVE`. No two versions of one ID may simultaneously hold current authority.

## Git boundary

Transitions are append-only **within an accepted Git history**. Projects identify the authoritative Git ref, normally a protected default branch. Other branches can validly disagree until merged. Git protects committed bytes and ancestry; this log has no hash chain. The protocol neither authenticates approvers nor enforces branch policy.

`convergence check` validates only shared files. It ignores optional `evidence/` and adapter output. It does not execute tests or inspect Git hosting settings.
