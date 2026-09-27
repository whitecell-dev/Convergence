# Convergence Constitution

This document exists to prevent Convergence from becoming the thing it was designed to replace.

---

## 1. Purpose

Convergence is a small, tool-independent way for a project to record what it currently considers authoritative.

> No matter which human, agent, IDE, model provider, CI system, or methodology touches the repository, there is one tool-independent representation of what the project currently considers authoritative.

That is the invariant this project must preserve.

---

## 2. Constitutional Constraint

**Convergence must remain useful without the software factory.**

The software factory — Ripwire, Compound Engineering, scaffolds, validators, MCP, small-model workers — is one sophisticated consumer and producer of Convergence.

It is not the reason Convergence exists.

If Convergence requires the factory to be useful, it has failed.
┌── Claude Code
├── Codex
├── Cursor
├── human developer
├── CI
├── tests
├── custom agents
├── software factory
└── future tool
│
▼
.convergence/
│
authoritative
project invariants

text

---

## 3. Terminology

An **invariant** is something the project has explicitly decided participants may rely upon within a stated scope.

An invariant is not limited to something formally provable.

A **rule** is one file-level representation of an invariant.

The constitution uses *invariant* because that describes what the artifact *is*.

The implementation uses *rule* because that describes how it is *represented*.

They refer to the same thing.

---

## 4. What an Invariant Is

An invariant is:

Something the project has explicitly decided participants may rely upon within a stated scope.

Example:

```json
{
  "id": "api.user-id-format",
  "version": 1,
  "scope": {"paths": ["src/api/"]},
  "constraint": "User IDs are UUIDv7.",
  "evidence_reference": "tests/test_user_ids.py",
  "oracle": null
}

A human can read it.
Claude can read it.
Codex can read it.
A shell script can parse it.
CI can enforce it.
A factory can compile it.

Its meaning must not change depending on the consumer.

5. Architecture: Evidence → Authorization → Invariant
Convergence is not concerned with how knowledge is discovered or enforced. It is concerned with what happens between.

text
different ways of learning
          │
          ▼
       evidence
          │
          ▼
     authorization
          │
          ▼
    project invariant
          │
          ▼
different ways of consuming / enforcing
Everything before and after is an adapter.

6. What Convergence Must NOT Become
This is a hard list. Any proposal that violates it must be rejected or moved to an adapter.

6.1 No mandatory dependency on a particular tool
Convergence must not require any single tool, model, methodology, or provider.

Not an agent framework. It does not run agents.

Not a model-dependent protocol. No specific LLM, provider, or context window.

Not an IDE plugin. No requirement on Cursor, Claude Code, Codex, or VS Code.

Not an MCP server requirement. MCP may expose Convergence. It must not be required to use it.

Not a factory requirement. No requirement on Ripwire, Compound Engineering, or any specific discovery methodology.

6.2 No mandatory infrastructure
Convergence must not require anything to be running.

Not a hosted service. No account, no SaaS, no mandatory backend for v0.

Not a database. No vector DB, no custom storage engine. Filesystem + Git is the storage.

Not a workflow engine. It does not own how work is scheduled.

6.3 No mandatory methodology
Convergence must not require any particular way of doing things.

Not an enforcement requirement. A rule with oracle: null is valid. Authority and mechanization are orthogonal.

Not a tool-standardization mandate. It must assume heterogeneity of tooling. Agreement is on the artifact, not the tooling.

6.4 Not the project's only source of truth
Convergence is not the project's only source of truth. It is the project's source of authority. Those are different.

Convergence sits beside Git, tests, design docs, and AGENTS.md. It does not replace them.

If a team starts deleting their design docs because "it's in Convergence now," the project has failed in a different way — not by becoming a framework, but by absorbing things it should not.

7. What Belongs in the Core
Only features that make project invariants more portable between tools.

Core:

Stable invariant IDs

Scope

Versioning

Human approval reference required for ACTIVE

Lifecycle derived from append-only transitions (no in-place mutation)

Counterevidence able to challenge ACTIVE → SUSPECT

UNRESOLVED as a valid outcome (unknown is different from wrong)

Evidence remains attributable to the invariant version that produced it

File contract as the interface

Not core: how evidence is found, how oracles are implemented, how invariants are distributed.

8. Test for Feature Creep
For every proposed feature, ask:

Does this make project invariants more portable between tools, or does it make Convergence dependent upon one particular way of working?

Proposal	Answer	Reason
Require Ripwire	No	One evidence producer
Require MCP	No	One distribution mechanism
Require Claude Code	No	Adapter
Require oracle for every rule	No	Mechanization is optional
Require the software factory	No	One consumer ecosystem
Rules need scope	Yes	Core
Authority needs versioning	Yes	Core
Counterevidence must challenge ACTIVE	Yes	Core
Invariant files are the interface	Yes	Core
9. The Interoperability Principle
Agreement is on the artifact, not the tooling.

Convergence files are the interface. Any implementation is merely one implementation of their semantics.

A team using only Git and three JSON files must be able to participate in the same protocol as a team running the full reference software factory.

This allows Convergence to stay tiny while its integration surface becomes enormous.

10. Success Criterion
Convergence succeeds if someone can say:

"I don't use any of Maykon's stack. But this ACTIVE/SUSPECT/UNRESOLVED thing with scoped, versioned invariants solves an annoying coordination problem on our team."

Level 0 adoption — clone the repo, read the idea, steal the file layout — is still successful adoption.

11. Amending the Constitution
This document is meant to survive the project's evolution.

Changes to sections 2, 6, or 9 require stating what new pressure or evidence justifies the change.

The default answer to any proposed expansion is no.

The burden of proof is on the expansion, not on the constraint.

The idea in one sentence
Convergence is a tool-independent representation of what a project currently considers authoritative.

Agents are allowed to diverge.

Projects need a way to converge.
