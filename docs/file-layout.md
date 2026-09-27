# Convergence v0 file contract

A project stores Convergence state in `.convergence/`:

```text
.convergence/
  README.md
  rules/
    <rule-id>.json
  transitions.jsonl
  evidence/
    executions.jsonl
    discover_candidates.jsonl
    revalidate_candidates.jsonl
```

The first write creates the directories, README, and empty ledgers. `rule-id`
uses letters, digits, `.`, `_`, and `-`, and begins with a letter or digit.
There is one current-content file per rule ID. A revision replaces that file;
state-only transitions do not edit it. `transitions.jsonl` preserves version
and authority history. Git can preserve earlier rule *content* after a
revision; this current-file layout alone does not.

## Rule content

A rule file is one JSON object. Required fields are `id` (string), `version`
(positive integer), `scope` (opaque JSON object), `constraint` (nonempty text
or JSON object), `oracle` (nonempty reference string or `null`), and
`evidence_reference` (nonempty reference string or `null`). Optional fields
are `exclusions` (list of strings) and `instruction` (string). Unknown fields
are invalid. The current authority state and approval reference are obtained
from transitions, not stored in the rule file. `record_rule` accepts
`authority_state: "ACTIVE"` as an input assertion and requires a separate
nonblank human `approval_reference`; neither becomes a mutable rule field.

`oracle: null` means the claim is authorized but lacks mechanical verification.
It does not imply `PROVEN`. A rule with an oracle reference still needs that
oracle to run on a WorkUnit before the WorkUnit can be PROVEN or VIOLATED.
The scope object has no built-in framework or path semantics. The default
resolver compares the keys supplied in a query for exact value equality.

For example, `scope: {"paths": ["src/api/"]}` matches a query of
`{"paths": ["src/api/"]}` and does not match `{"paths": ["src/other/"]}`.
For Click, `scope: {"framework": "click", "primitive": "option",
"operation": "generate"}` matches that same three-key query. The core
applies the same equality check in both cases; an adapter may supply a
different matcher.

## Lifecycle transitions

Each line of `transitions.jsonl` is a JSON object. Records are ordered:

| Event | Fields besides `event` | Effect |
| --- | --- | --- |
| `RULE_RECORDED` | `rule_id`, `rule_version`, `approval_reference` | Registers a version in CANDIDATE state. |
| `RULE_ACTIVE` | `rule_id`, `rule_version` | Sets ACTIVE. |
| `RULE_CHALLENGED` | `rule_id`, `rule_version`, `candidate_id` | Sets SUSPECT. |
| `RULE_REVISED` | `rule_id`, `rule_version`, `new_version` | Links an old version to its approved successor; does not itself change state. |
| `RULE_RETIRED` | `rule_id`, `rule_version` | Sets RETIRED. |
| `CANDIDATE_RESOLVED` | `candidate_id`, `resolution`, `approval_reference` | Closes one candidate; `resolution` is ACTIVE, REVISED, or RETIRED. |

Recording v1 emits RULE_RECORDED and RULE_ACTIVE. Recording v2 emits
RULE_REVISED and RULE_RETIRED for v1, then RULE_RECORDED and RULE_ACTIVE for
v2. It also resolves open v1 REVALIDATE candidates as REVISED with the same
human approval reference. Resolving a challenge as ACTIVE emits
CANDIDATE_RESOLVED then RULE_ACTIVE. Resolving it as RETIRED emits
CANDIDATE_RESOLVED then RULE_RETIRED. A DISCOVER candidate may be closed by a
human decision, but that closure does not itself create an active rule.

To derive state, fold transitions in file order, keyed by `(rule_id,
rule_version)`: RECORDED → CANDIDATE, ACTIVE → ACTIVE, CHALLENGED → SUSPECT,
RETIRED → RETIRED. REVISED records a version link. CANDIDATE_RESOLVED marks a
candidate closed. The current rule file supplies the latest rule content;
its `authority_state` and `approval_reference` are joined from that fold.
Only candidates without a resolution transition are open.

## Execution evidence

Each `evidence/executions.jsonl` line contains exactly `work_unit_id` (string),
`rule_id` (string or `null`), `rule_version` (integer or `null`),
`artifact_hash` (SHA-256 text), `applicable` (boolean), `oracle_ran` (boolean),
`oracle_result` (`pass`, `violated`, `unavailable`, or `not_applicable`), and
`outcome` (PROVEN, VIOLATED, or UNRESOLVED). The execution identity is
`(work_unit_id, rule_id, rule_version, artifact_hash)`. A repeated identity
returns the existing record and does not append. The artifact itself is not
copied into `.convergence/`.
Before appending a new execution, the recorder reads current authority from
the rule file and transitions. A repeated identity returns its saved record
even if that rule has since become SUSPECT or RETIRED.

## Candidate evidence

Each line in the two candidate files contains exactly `candidate_id`, `kind`,
`state`, `reason`, `work_unit_id`, `rule_id`, `rule_version`, and
`artifact_hash`. `kind` is DISCOVER or REVALIDATE. The initial `state` is
DISCOVER or SUSPECT respectively; open/resolved status comes from transitions.
The candidate identity is `(kind, work_unit_id, rule_id, rule_version,
artifact_hash)`. `candidate_id` is the lowercase SHA-256 hex digest of the
UTF-8 JSON encoding of that tuple as an array, using compact separators
`(',', ':')` and default JSON escaping. Repeated identities return the saved
candidate. REVALIDATE also writes RULE_CHALLENGED. A null oracle routes an
unresolved WorkUnit to DISCOVER, leaving its rule ACTIVE.

## Integrity boundary

`check_protocol_integrity(root)` returns an empty list for a valid store or
specific error strings. It checks rule schemas, transition references and
version order, execution references and duplicate identities, candidate
references and duplicate identities, orphaned challenge/resolution events,
and the required paths in this layout.
It does not run an oracle, authenticate an approval reference, rehash old
artifacts, prove that external edits never occurred, or serialize concurrent
writers. The v0 writer uses a linear ledger scan; projects with concurrent
writers must coordinate writes outside this protocol, such as through Git.
