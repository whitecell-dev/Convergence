# Click replay specification

The core accepts an unresolved WorkUnit execution, an artifact hash, active
rules with explicit approval references, a supplied structural fixture, and
oracle observations. It returns resolved rules, a consumer bundle, append-only
execution records, and DISCOVER or REVALIDATE candidates. The archived
`unknown1` record has no applicable argument rule and is `UNRESOLVED`; the
saved candidate is DISCOVER. The option-only case is explained in
[`DISCOVER.md`](../../Semantic-Extractor/docs/experiments/click-learning-cycle/DISCOVER.md)
and the exact records are in
[`before/executions.jsonl`](../../Semantic-Extractor/docs/experiments/click-learning-cycle/before/executions.jsonl)
and [`before/discovery_candidates.jsonl`](../../Semantic-Extractor/docs/experiments/click-learning-cycle/before/discovery_candidates.jsonl).

The slow path is observation → candidate → evidence → stabilized → active.
The first three steps occur outside this core: the Click investigation used
source tracing, two independent positive probes, and a negative callback
counterexample before a human accepted the narrow v1 diff. Only that explicit
decision permits `record_rule` to write ACTIVE v1. The maintenance challenge
produces SUSPECT when v1 applies but its oracle cannot run. A second human
decision authorizes v2 and retires v1; the excluded case then becomes
UNRESOLVED and DISCOVER again. Evidence and decision are recorded in
[`REVALIDATE.md`](../../Semantic-Extractor/docs/experiments/click-maintenance/REVALIDATE.md),
[`revalidation_record.json`](../../Semantic-Extractor/docs/experiments/click-maintenance/revalidation_record.json),
and the two authored diffs
([v1](../../Semantic-Extractor/docs/experiments/click-learning-cycle/authored-rule.diff),
[v2](../../Semantic-Extractor/docs/experiments/click-maintenance/revision.diff)).

| Responsibility | Input → output | Failure mode | Click evidence |
| --- | --- | --- | --- |
| Represent | Approved rule + approval reference → ACTIVE version; revision retires prior version | Missing approval, bad version, duplicate version | v1 and v2 authored diffs; maintenance decision |
| Resolve | Framework, primitive, operation → active applicable rules | Wrong scope, unapproved rule | Option-only gap in `DISCOVER.md`; v2 exclusion in `REVALIDATE.md` |
| Compile | Active rules + supplied structural fixture → consumer bundle | Missing oracle projection or fixture drift | v1/v2 parity and reruns in `REVALIDATE.md` |
| Record | WorkUnit, artifact, oracle observation → immutable execution | Stale hash, stale rule, missing oracle | `before/`, `after/`, `suspect/`, `post_decision/` execution records |
| Route | UNRESOLVED execution → DISCOVER or SUSPECT/REVALIDATE candidate | False proof or wrong candidate queue | `click-feedback/evidence/` and maintenance candidate records |

The rule fields are all exercised: `id` ties v1 to v2; `version` preserves
attribution; `scope` selects Click option generation; `exclusions` gains
`expose_value=False`; `constraint` states the callback keyword claim;
`oracle` identifies its check; `approval_reference` records each human
decision; `state` distinguishes ACTIVE and RETIRED. The replay also retains
the historical `instruction` text because the exact authored worker rule
includes it. See the [Click invariants table](../../Semantic-Extractor/Python/boilerplate-generator/semantic/tables/click/invariants.json).

An execution needs `work_unit_id` to link the records, `rule_id` and
`rule_version` to attribute the check, `artifact_hash` to show the source is
unchanged, `applicable` and `oracle_ran` to distinguish missing knowledge from
counterevidence, `oracle_result` to distinguish pass, violation, and
unavailability, and `outcome` to route the fast loop. The saved
[`after/executions.jsonl`](../../Semantic-Extractor/docs/experiments/click-learning-cycle/after/executions.jsonl)
and [`suspect/executions.jsonl`](../../Semantic-Extractor/docs/experiments/click-maintenance/suspect/executions.jsonl)
contain all of these distinctions.

A candidate needs `kind` and `state` to separate DISCOVER from SUSPECT
revalidation, `reason` to say why it was routed, `work_unit_id` and
`artifact_hash` to locate the observation, and challenged rule ID/version
only for revalidation. The saved
[`discovery_candidates.jsonl`](../../Semantic-Extractor/docs/experiments/click-learning-cycle/before/discovery_candidates.jsonl)
and [`revalidation_candidates.jsonl`](../../Semantic-Extractor/docs/experiments/click-maintenance/suspect/revalidation_candidates.jsonl)
show those cases. The core stores candidate files append-only; it does not
stabilize or author claims.

The supplied [Click fixture](../../Semantic-Extractor/Python/IR-files/calyx_click_v6.json)
predates v1. Replay parity therefore means its parsed structural fields are
unchanged in the generic bundle, while rule fields match the authored v1 and
v2 objects. This does not reproduce the old compiler's source-to-bundle
process, its CALYX consumer format, or prove a second framework will fit.
