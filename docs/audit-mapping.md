# Adoption audit → schema work

| Audit finding | Change here | Check |
| --- | --- | --- |
| §4, §8: the UUIDv7 claim was rejected without an invented oracle; §11 calls this a core gap. | Keep `authority_state` in the lifecycle, permit `oracle: null`, and record the test path as `evidence_reference`. The approval reference still gates ACTIVE. | `test_generic_claim.py` records and reloads the claim with no oracle. |
| §4, §8: `src/api/` had to be translated to `framework/primitive/operation`. | Treat scope as an opaque dictionary; resolve by supplied-key equality unless an adapter supplies a matcher. | Generic path query and unchanged Click replay. |
| §2, §5, §8: a per-rule file was ignored; after a challenge the rule reloaded ACTIVE because SUSPECT existed only in a candidate queue. | Use `.convergence/rules/<id>.json` for current rule content and append lifecycle events to `transitions.jsonl`; derive state by folding events. | Generic reload, Click v1→v2 replay, idempotence status checks. |
| §2, §5, §6: replay duplicated executions and candidates; there was no open/historical distinction or persisted-ledger validation. | Use stable execution/candidate identities, resolution events, and a protocol integrity reader. | `test_idempotence.py` and `test_integrity.py`. |

The audit's §12 found no sixth responsibility. These changes stay in represent,
resolve, compile, record, and route. Execution and candidate evidence remain
append-only. Only a nonblank human approval reference can activate or resolve
an authoritative claim. The Click oracle and its three outcomes stay intact.
