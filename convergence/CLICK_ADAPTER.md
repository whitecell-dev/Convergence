# Click adapter boundary

`click_adapter.evaluate(artifact, rule)` checks the narrow literal long-option
binding shape established by the Click learning experiment. It parses the
supplied artifact only to run the rule oracle. It neither extracts Click's
structural IR nor writes rules or bundles.

Structural evidence is an input. `integrations.ripwire.read_structural_ir`
accepts an existing Ripwire JSON map or the archived Click structural fixture.
The Ripwire fork does not currently emit the fixture's CALYX schema, so the
saved fixture is used for the replay. Neither reader grants authority.

The adapter's minimum interface is a rule schema (the fields accepted by
`AuthorityStore`) and `evaluate(artifact, rule)` returning `rule_id`,
`rule_version`, `applicable`, `oracle_ran`, and `oracle_result`.
