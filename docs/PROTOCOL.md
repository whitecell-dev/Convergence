# Convergence protocol

Convergence records what a project currently authorizes people and tools to rely on. It owns the transition between evidence and authority, not the systems that produce evidence or use claims.

```text
CANDIDATE → AUTHORIZED → ACTIVE
                           ├→ RETIRED
                           └→ SUSPECT → AUTHORIZED → ACTIVE
                                    ├→ SUPERSEDED (new version starts CANDIDATE)
                                    └→ RETIRED
CANDIDATE → WITHDRAWN
```

An ACTIVE version may be SUPERSEDED directly when a new version replaces it. A claim file begins in CANDIDATE even without an explicit event. AUTHORIZED requires a nonblank approval reference. That pointer attributes a human decision; it does not authenticate anyone. Repository review policy provides trust. A separate ACTIVE transition permits reliance.

Counterevidence against an ACTIVE claim makes it SUSPECT. Consumers must exclude SUSPECT claims from new work. Each challenge has a `counterevidence_ref`; restoration of the same version must resolve all outstanding references. Counterevidence against a CANDIDATE remains evidence for the proposal and does not create a SUSPECT state.

Claim content is immutable per version. Revision creates a new version and SUPERSEDED links the old one. `REVISED` is not a state. Retained version files preserve old claims without Git history.

Only `rules/` and `transitions.jsonl` are required. An independent implementation can fold those files to determine authority. Normative fields and event shapes are in [file-layout.md](file-layout.md). Factory discovery, execution, and routing loops are outside the protocol.
