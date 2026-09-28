# Convergence

> **You are on the `experiment` branch.** This is the opinionated implementation: a software-factory loop with evidence ledgers, oracle compilation, routing, and a Click proof of concept. It is heavier than the protocol requires and is not the recommended starting point.
>
> For the narrow protocol — two required files, no dependencies, free to adopt — use [`main`](https://github.com/whitecell-dev/Convergence). The protocol is normative there; this branch is one implementation of it plus the machinery around it.

**A place for your project to record what it has decided it can rely on.**

Projects accumulate rules. They end up in tests, docs, prompts, comments, Slack threads, and people's heads.

Convergence gives those rules a small, Git-native home with scope, evidence, approval, versioning, and lifecycle.

No server. No account. No database. No required agent. No required workflow.

Start with a directory.

```bash
convergence init
```

### The five-minute version

Create `.convergence/`:

```
.convergence/
├── README.md
├── rules/
├── transitions.jsonl
└── evidence/
```

Write one rule:

```json
{
  "id": "api.user-id-format",
  "version": 1,
  "scope": {"paths": ["src/api/"]},
  "constraint": "User IDs are UUIDv7.",
  "oracle": null,
  "evidence_reference": "tests/test_user_ids.py"
}
```

Record its approval:

```json
{"event":"RULE_RECORDED","rule_id":"api.user-id-format","rule_version":1,"approval_reference":"PR-381"}
{"event":"RULE_ACTIVE","rule_id":"api.user-id-format","rule_version":1}
```

That's it. Your project now has one piece of authoritative knowledge, in a place that Git, humans, agents, and CI can all read.

### The distinction that matters

*Evidence is not authority.*

Something observed by a developer, agent, test, runtime probe, or external tool can inform a project decision. It does not silently become one.

Convergence records the transition from something we observed to something the project has explicitly decided it may rely on.

This is enforced by the file contract: ACTIVE rules require an approval reference. An oracle may legitimately be null — a rule can be authoritative before it is mechanically checkable.

Authority and mechanization are orthogonal.

### The lifecycle

```
OBSERVATION
     ↓
  DISCOVER
     ↓
 CANDIDATE
     ↓
   human
 authority
     ↓
   ACTIVE ──────────────┐
     │                   │
     │ execution         │ counterevidence
     ↓                   ↓
  PROVEN              SUSPECT
  VIOLATED               │
  UNRESOLVED             │
                         ↓
                 ACTIVE / REVISED / RETIRED
```

Rules are content. Lifecycle is derived from append-only transitions. Nothing mutates in place.

`UNRESOLVED` is a valid outcome. The system prefers admitting it does not know over silently manufacturing certainty.

### No dependency required

Convergence is a file protocol first.

You do not need our CLI, our agents, Ripwire, Compound Engineering, MCP, or a particular LLM.

Create `.convergence/`, follow the file contract, and commit it to Git.

The reference implementation exists to make that easier and to mechanically check the protocol. It is optional.

### Why this becomes useful

With one developer, Convergence is a place for rules.

With a team, it becomes something else.

Git tells everyone what changed.
Tests tell everyone whether something passes.
Documentation tells everyone what someone wrote down.

Convergence gives them a shared answer to a different question:

> What has this project currently decided it can rely on?

Each participant — human or agent — can develop locally reasonable beliefs. Those beliefs are allowed to diverge. The project's authoritative knowledge is not.

*Agents may diverge. Projects must converge.*

### A worked example: Click

The initial proof of concept was tested against Click framework semantics.

A previously unknown option-binding behavior produced an UNRESOLVED WorkUnit.

Investigation established a narrow candidate rule. After human authorization, it became:

`click.option.callback_keyword_binding@1`

The rule was compiled and mechanized. The previously unresolved WorkUnit became PROVEN. A same-class WorkUnit became PROVEN. A deliberately incorrect binding became VIOLATED.

Later, a real counterexample appeared:

```python
@click.option("--value", expose_value=False)
```

Version 1 incorrectly claimed that case. Execution challenged the project's existing knowledge rather than treating the artifact as a worker failure.

The rule became SUSPECT. After review, its scope was narrowed and version 2 became ACTIVE:

```
click.option.callback_keyword_binding@1
              ACTIVE
                 │
        expose_value=False
          counterexample
                 │
                 ↓
              SUSPECT
                 │
           human review
                 │
                 ↓
             REVISED
                 │
                 ↓
click.option.callback_keyword_binding@2
              ACTIVE
```

The original valid WorkUnits remained proven. The negative control remained violated. The newly excluded behavior became UNRESOLVED rather than falsely proven — and routed back to DISCOVER.

That is the property being demonstrated:

> The system can learn something, rely on it, discover that its understanding was too broad, and reconverge without silently rewriting history.

### What Convergence is not

Not a knowledge base.
Not a test framework.
Not a linter.
Not an agent framework.
Not an MCP server.
Not a replacement for Git, CI, AGENTS.md, or design docs.
Not a requirement to use any particular software factory.

### Integrate whatever you already use

```
Claude Code ─┐
Codex ───────┤
Cursor ──────┤
Humans ──────┤── .convergence/ ── Git
CI ──────────┤
pytest ──────┤
Ripwire ─────┤
anything ────┘
```

Agreement is on the artifact, not the tooling.

### The file contract

```
.convergence/
├── README.md
├── rules/
│   └── <rule-id>.json
├── transitions.jsonl
└── evidence/
    ├── executions.jsonl
    ├── discover_candidates.jsonl
    └── revalidate_candidates.jsonl
```

Rules hold claim content. They do not hold authority state.
Transitions hold lifecycle events. Current state is derived by folding them.
Evidence holds append-only execution records and unresolved candidates.

The full specification is in `docs/file-layout.md`.

### Design principles

- Evidence is not authority.
- Unknown is different from wrong.
- Authority must be scoped and versioned.
- Counterevidence must be able to challenge authority.
- Historical evidence should remain attributable to the rule version that produced it.
- Probabilistic intelligence may propose authority changes; it should not silently grant itself authority.
- Once knowledge can be mechanized, stop spending model intelligence rediscovering it.
- Integrate commodity infrastructure. Own only the semantics introduced by probabilistic work.

### Why this matters for software factories

LLM economics are dominated by repeated reasoning.

Without accumulated project semantics:

```
worker encounters problem
        ↓
reason about framework
        ↓
search
        ↓
experiment
        ↓
maybe solve it
        ↓
conversation ends
        ↓
next worker starts again
```

With Convergence:

```
expensive discovery once
        ↓
stabilize
        ↓
authorize
        ↓
mechanize
        ↓
cheap application N times
```

Frontier intelligence pays the discovery cost once. Humans decide what becomes trusted. Infrastructure pays the application cost thereafter.

### This will make your rules survive you

With one developer, Convergence is a place for rules.
With two, it is a place to disagree about them.
With ten, it is a place where the project, not any individual conversation, is the persistent unit of understanding.

You don't need any of that today. You just need a directory.

```bash
convergence init
```

### Status

Convergence is currently an experimental protocol derived from a narrow Click proof of concept.

The current work demonstrates the basic learning and maintenance cycles, including human-gated graduation, versioning, execution evidence, applicability, PROVEN / VIOLATED / UNRESOLVED outcomes, counterevidence, and reconvergence.

It does not establish a general solution for arbitrary frameworks or unattended semantic maintenance.

That's intentional.

### The idea in one sentence

> Convergence is the protocol by which distributed learning becomes shared, versioned, mechanically enforceable project knowledge.
