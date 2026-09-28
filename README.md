# Convergence

Convergence is a Git-native place for project claims that people have authorized others to rely on.

> **Protocol boundary:** Convergence stores versioned claims, evidence references, approval references, and authority transitions. It does not discover or evaluate evidence, execute tests, retrieve documents, instruct agents, or enforce claims.
>
> **Authority rule:** Evidence, tests, CI, and model judgments never authorize a claim by themselves. Authorization is an explicit transition citing a human decision. The reference is attribution, not authentication; repository governance such as protected branches, CODEOWNERS, and review rules supplies trust.
>
> **Conformance:** Only versioned claim content in `.convergence/rules/` and `.convergence/transitions.jsonl` are required. No CLI, service, model, oracle, WorkUnit, or factory is needed.

## Hand-written example

```text
.convergence/
  rules/
    api.user-id-format/
      v1.json
  transitions.jsonl
```

`rules/api.user-id-format/v1.json`:

```json
{"id":"api.user-id-format","version":1,"scope":{"paths":["src/api/"]},"claim":"User IDs are UUIDv7.","evidence_refs":["git:abc123:tests/test_user_ids.py"]}
```

`transitions.jsonl`:

```json
{"event":"AUTHORIZED","id":"api.user-id-format","version":1,"approval_ref":"PR-381"}
{"event":"ACTIVE","id":"api.user-id-format","version":1}
```

`ACTIVE` permits reliance on this claim within its scope. `CHALLENGE` makes it `SUSPECT`; consumers must stop treating it as authoritative for new work until resolved. See [the file contract](docs/file-layout.md).

## Optional CLI

```sh
convergence init
convergence add --id api.user-id-format --claim 'User IDs are UUIDv7.' --scope src/api/ --evidence-ref git:abc123:tests/test_user_ids.py
convergence authorize --id api.user-id-format --version 1 --approval-ref PR-381
convergence activate --id api.user-id-format --version 1
convergence status
convergence check
```

`add` writes a CANDIDATE to a versioned path. `authorize` records the human decision; `activate` permits use. CLI commands accept a repository path as a positional argument. A hand-written `rules/<id>.json` file is also accepted.

The authoritative set comes from the repository's chosen Git ref, usually its protected default branch. Transitions are append-only within an accepted Git history. Git supplies integrity for committed bytes; Convergence adds authority semantics, not a second hash chain.

The [protocol](docs/PROTOCOL.md) is normative. [Factory examples](examples/factory/) are optional.
