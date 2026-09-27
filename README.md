# Convergence

**The protocol by which distributed learning becomes shared project knowledge.**

Modern software projects no longer have one coherent author.

They have engineers using different models, coding agents running independently, CI systems, runtime telemetry, static analyzers, documentation, issue trackers, and humans carrying context that may never have been written down.

Those participants are allowed to disagree.

**The project can't.**

Convergence is a small protocol for deciding how observations become knowledge a project is allowed to rely on—and how that knowledge is challenged, revised, and eventually retired.

It is not an agent framework. It does not require a particular model, IDE, retrieval system, or execution harness.

It provides a shared answer to one question:

> **What is this project currently allowed to rely on, and why?**

---

## The problem

Git tells us **what changed**.

CI tells us **whether a check passed**.

RAG tells an agent **what information it can retrieve**.

`AGENTS.md`, `CLAUDE.md`, documentation, and engineering notes tell agents **what someone wrote down**.

None of those establish that a claim is currently authoritative.

This becomes increasingly painful as more humans and agents work on the same project.

```text
Engineer A + Claude ──────┐
Engineer B + Codex ───────┤
Engineer C + Cursor ──────┤
CI ───────────────────────┤
Runtime observations ─────┤
Static analysis ──────────┤
                          ▼
                    ??? shared truth
```

Each participant can develop a locally reasonable understanding of the system while the project as a whole quietly diverges.

More context does not solve this.

Better retrieval does not solve this.

Making every worker use the same model does not solve this.

The missing primitive is a protocol for **convergence**.

---

## The principle

Convergence separates **evidence** from **authority**.

An agent discovering something does not make it true.

A document containing something does not make it true.

A test passing once does not make it universally true.

A model confidently proposing a rule does not make that rule authoritative.

Knowledge instead moves through explicit states:

```text
OBSERVATION
    │
    ▼
CANDIDATE
    │
    ▼
EVIDENCE
    │
    ▼
STABILIZED
    │
    │ human authority
    ▼
ACTIVE
    │
    ├───────────────► applied mechanically
    │
    │ counterevidence
    ▼
SUSPECT
    │
    ├──► REVISED ──► ACTIVE @ next version
    │
    └──► RETIRED
```

`UNRESOLVED` is a valid result.

The system should prefer admitting that it does not know over silently manufacturing certainty.

---

# The knowledge lifecycle

Convergence operates as two connected loops.

## Slow loop: learn

### 1. Discover

Real work encounters something the project does not understand.

A frontier model, developer, runtime probe, static analyzer, or other investigative tool can establish evidence.

The important artifact is not an answer.

It is a **candidate claim with evidence**.

### 2. Capture

Record what happened:

- observation
- suspected cause
- failed approaches
- successful probes
- counterexamples
- evidence
- unresolved questions

This is useful knowledge, but it is not authoritative knowledge.

### 3. Stabilize

Test whether the observation survives beyond the motivating example.

Use additional WorkUnits, runtime probes, negative controls, source inspection, or independent validation.

A repeated observation can become a candidate rule.

It still has no authority.

### 4. Authorize

This is the boundary.

A human reviews the evidence and determines the exact claim the project is willing to rely upon.

The result should have at least:

```text
id
version
scope
exclusions
constraint
oracle
approval reference
state
```

Probabilistic systems may propose changes to authority.

They do not acquire authority merely by proposing them.

### 5. Graduate

The authorized claim enters the project's canonical semantic representation.

For example:

```json
{
  "id": "click.option.callback_keyword_binding",
  "version": 2,
  "state": "ACTIVE",
  "scope": {
    "framework": "click",
    "primitive": "option",
    "operation": "generate"
  },
  "exclusions": [
    "expose_value=false"
  ],
  "oracle": "click_validator:option.callback_keyword_binding"
}
```

The rule can now be compiled, resolved, distributed, and referenced mechanically.

### 6. Mechanize

Turn semantics into infrastructure.

Depending on the claim, that might mean:

- static validation
- AST checks
- runtime probes
- generated tests
- scaffold constraints
- deterministic transforms
- correct-by-construction generation

The goal is simple:

> **Stop requiring workers to remember things the environment can enforce.**

---

# Fast loop: execute

Once knowledge has graduated, ordinary work should be boring.

```text
WorkUnit
   │
   ▼
Resolve applicable semantics
   │
   ▼
Construct bounded environment
   │
   ▼
Execute worker
   │
   ▼
Run oracle
   │
   ├── PROVEN ─────► continue
   │
   ├── VIOLATED ───► reject/correct
   │
   └── UNRESOLVED
            │
            ├── missing knowledge ──► DISCOVER
            │
            └── trusted rule failed ► REVALIDATE
```

The fast loop executes.

The slow loop learns.

Execution continuously supplies evidence back to the knowledge lifecycle.

---

# Reconvergence

Authoritative does not mean permanently correct.

Reality changes.

Dependencies change. Frameworks change. Code changes. New edge cases appear. Old assumptions stop holding.

When execution produces counterevidence against an ACTIVE rule, Convergence does not silently ignore the evidence or immediately let an agent rewrite the rule.

It marks the claim for revalidation:

```text
ACTIVE @1
    │
    │ counterevidence
    ▼
SUSPECT
    │
    ▼
REVALIDATE
    │
    │ human decision
    ▼
REVISED
    │
    ▼
ACTIVE @2
```

Historical evidence remains attached to the version that produced it.

This makes project knowledge **revisable without becoming arbitrary**.

---

# Why this is not RAG

RAG answers:

> What relevant information can I retrieve?

Convergence answers:

> What information is this project currently allowed to rely upon?

These are complementary.

A discovery agent might use RAG to find an old engineering note. But retrieving the note does not grant it authority.

```text
RAG
"What have we said about this?"

Convergence
"What have we established about this?"
```

RAG is useful throughout investigation.

Graduated semantics should eventually stop being merely retrieved and become mechanically applicable.

---

# Why this is not `AGENTS.md`

Agent instruction files are excellent for communicating conventions.

They are still text.

They generally cannot distinguish:

```text
hypothesis
observation
old convention
current rule
challenged rule
retired rule
```

And an agent can misunderstand or ignore them.

Convergence adds lifecycle, scope, evidence, versioning, and enforcement.

`AGENTS.md` can be a consumer or projection of Convergence.

It is not the authority mechanism itself.

---

# Why this is not Git

Git provides an authoritative history of **bytes**.

Convergence provides an authoritative history of **claims**.

Git can tell you:

```text
rule changed from v1 → v2
```

Convergence records why:

```text
v1
 │
 │ runtime counterexample
 ▼
SUSPECT
 │
 │ evidence + human decision
 ▼
v2
```

Convergence should use Git rather than replace it.

---

# Why this is not CI/CD

CI is an enforcement mechanism.

That makes it an excellent consumer of Convergence.

But CI usually knows:

```text
PASS
FAIL
```

Convergence needs another state:

```text
UNRESOLVED
```

Those outcomes mean different things.

A violation says:

> We know the rule, and this artifact violated it.

An unresolved result says:

> We do not currently possess sufficient authoritative semantics to prove this artifact.

The first is an execution problem.

The second is a learning event.

Collapsing them loses information.

---

# Heterogeneous agents are expected

Convergence does not require every engineer to use the same tools.

One team might have:

```text
Claude
Codex
Cursor
pytest
GitHub Actions
Jira
```

Another might have:

```text
local model
Ripwire
Compound Engineering
custom validators
MCP
```

Both can use the same protocol.

Workers may differ in intelligence, provider, context window, prompting strategy, or implementation.

They don't need identical internal beliefs.

They need a shared mechanism for determining what the **project** relies upon.

> **Agents may diverge. Projects must converge.**

---

# Reference architecture

Convergence itself should remain small.

```text
                 ┌──────────────────────┐
                 │     CONVERGENCE      │
                 │                      │
                 │ claims + versions    │
                 │ applicability        │
                 │ compilation          │
                 │ evidence             │
                 │ routing              │
                 └──────────┬───────────┘
                            │
          ┌─────────────────┼─────────────────┐
          ▼                 ▼                 ▼
      Validator         Generator            MCP
          │                 │                 │
          ▼                 ▼                 ▼
      CI / Agent        Scaffold         Any worker
```

A minimal implementation needs five responsibilities:

1. **Represent** authoritative claims and their lifecycle.
2. **Resolve** which claims apply to a WorkUnit.
3. **Compile** authoritative claims into consumer-friendly representations.
4. **Record** execution evidence without rewriting history.
5. **Route** missing knowledge and counterevidence back into the appropriate learning loop.

Everything else can be integrated.

---

# Reference software factory

Convergence came out of a more opinionated software-factory architecture.

That reference implementation uses tools such as:

```text
Frontier intelligence
        +
     Ripwire
        │
        ▼
     Discover
        │
        ▼
Compound Engineering
        │
        ▼
    Stabilize
        │
        ▼
   CONVERGENCE
        │
        ▼
MCP / compiled semantics
        │
        ▼
Scaffolds + bounded workers
        │
        ▼
Deterministic oracles
        │
        └──────── evidence ───────► Convergence
```

Those dependencies are not requirements of the protocol.

They demonstrate what happens when the loop is wired all the way through.

---

# Click proof of concept

The initial implementation was tested against Click framework semantics.

A previously unknown option-binding behavior produced an `UNRESOLVED` WorkUnit.

Investigation established a narrow candidate rule. After human authorization, it became:

```text
click.option.callback_keyword_binding@1
```

The rule was compiled and mechanized.

The previously unresolved WorkUnit became `PROVEN`, another same-class WorkUnit became `PROVEN`, and a deliberately incorrect binding became `VIOLATED`.

Later, a real counterexample appeared:

```python
@click.option("--value", expose_value=False)
```

Version 1 incorrectly claimed that case.

Execution therefore challenged the project's existing knowledge rather than treating the artifact as an ordinary worker failure.

The rule became `SUSPECT`.

After review, its scope was narrowed and version 2 became ACTIVE:

```text
click.option.callback_keyword_binding@1
               │
          counterexample
               ▼
            SUSPECT
               │
             review
               ▼
click.option.callback_keyword_binding@2
```

The original valid WorkUnits remained proven.

The negative control remained violated.

The newly excluded behavior became unresolved rather than falsely proven.

That is the intended property:

> **The system can learn something, rely on it, discover that its understanding was too broad, and reconverge without silently rewriting history.**

---

# Why this matters for software factories

LLM economics are dominated by repeated reasoning.

Without accumulated project semantics:

```text
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

Convergence lets that become:

```text
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

Frontier intelligence pays the discovery cost once.

Humans decide what becomes trusted.

Infrastructure pays the application cost thereafter.

That allows smaller models to operate successfully because increasingly little intelligence is required at execution time.

The environment has already learned.

---

# Why this matters for teams

The larger goal is not merely better autonomous coding.

It is making human-agent collaboration scale beyond:

```text
one engineer
+
their preferred agent
+
their private context
```

A project with ten engineers and twenty agents should not require thirty synchronized conversations.

Instead, each participant can independently contribute observations while sharing the same authoritative project state.

```text
distributed observation
        ↓
       evidence
        ↓
    convergence
        ↓
shared semantics
        ↓
mechanization
        ↓
distributed execution
```

The project becomes the persistent unit of understanding rather than any individual conversation.

---

# Design principles

**Evidence is not authority.**

**Unknown is different from wrong.**

**Authority must be scoped and versioned.**

**Counterevidence must be able to challenge authority.**

**Historical evidence should remain attributable to the rule version that produced it.**

**Probabilistic intelligence may propose authority changes; it should not silently grant itself authority.**

**Once knowledge can be mechanized, stop spending model intelligence rediscovering it.**

**Integrate commodity infrastructure. Own only the semantics introduced by probabilistic work.**

---

# Status

Convergence is currently an experimental protocol derived from a narrow Click proof of concept.

The current work demonstrates the basic learning and maintenance cycles, including human-gated graduation, versioning, execution evidence, applicability, `PROVEN / VIOLATED / UNRESOLVED` outcomes, counterevidence, and reconvergence.

It does **not** establish a general solution for arbitrary frameworks or unattended semantic maintenance.

That's intentional.

The immediate goal is to make the smallest useful convergence protocol work end-to-end before expanding the surface area.

---

## The idea in one sentence

> **Convergence is the protocol by which distributed learning becomes shared, versioned, mechanically enforceable project knowledge.**

Agents are allowed to diverge.

**Projects need a way to converge.**
