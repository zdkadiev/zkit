# Consistency review brief (earlier steps ↔ architecture)

Give this to a fresh reviewer sub-agent with the paths of `concept.md`, `requirements.md`, `resource-math.md` (with `resource-math/model.py`), `contracts.md` (with `contracts/`), `data.md`, `decisions.md` and `architecture.md` of the project (whichever exist). The reviewer reads them fully, edits nothing, reports in the developer's language, and returns at most 25 rows `type | where (B-/I-/S-/D-/DC- id or section) | what is wrong | suggested fix`, most serious first, then a one-paragraph verdict (consistent / minor issues / serious issues). Categories:

1. UNCOVERED: a Must requirement (or a v1-scope capability in the concept) that no part, interface or decision actually delivers - including ones the traceability table claims but the part's responsibility does not support.
2. NFR_NOT_MET: a scenario walk-through, or the structure itself, that fails a numeric NFR (restart loses state, a bypass of the approval point, one part owning state that two others write, a cost the structure cannot keep under the budget).
3. OVERBUILT: a part, interface or decision that serves no requirement and no stated driver, or a structure far heavier than the load profile needs.
4. CONTRADICTION: the design contradicts a requirement, constraint, concept boundary or non-superseded decision.
5. STALE: the design relies on a superseded decision or on an old version of a requirement, contract, number or entity.
6. STATE_OWNERSHIP: a piece of state or an entity with no owner or with two writers; an interface whose delivery semantics (idempotent, at-most-once, ordered) are missing where a requirement needs them.
7. BOUNDARY_GAP: a contract boundary `X-n` no part really handles, a part that bypasses the part that guards a boundary, or a contract the architecture makes impossible to honour (and was not revised).
8. NUMBERS_BROKEN: a resource-math limit or ceiling no part carries or that the structure violates; a technology choice whose price or capacity contradicts resource-math; an entity's storage class that its engine cannot serve.
9. TECH_CHOICE: a product chosen without options, evidence and a decision; a product chosen for a cheap-to-reverse concern (noise); an expensive concern left open that blocks the next steps.
10. LEAK_OR_DRIFT: content that belongs to a later step (algorithms, field-level schemas, internal machine-readable contracts, libraries, C4 level 4), or diagrams, parts table, interfaces table and scenarios that disagree about which parts exist or how they connect.

11. EXCHANGE_IDENTITY: check the participant roles and the agreement that identifies each I-n. Fan-out of one event contract retains one ID and identifies each recipient's effects. Distinct guarantees between the same participants remain distinguishable.
12. PROTOCOL_AND_EFFECTS: check that the named protocol explains the convention the parties rely on, including compatibility or versioning where relevant. Each read or change names its part, operation and entity. Verify that it matches ownership, the stated guarantees and any cited mechanism. Accept explicit stateless exchanges and effects described before mechanics exists. Once mechanics exists, follow the I-n to its spec and the MC-n to the rule governing the effect.
13. NAVIGATION: verify part containment, sender and recipient order, alternate paths, and links to memory and resource-math records against the authoritative tables. Check only the scope and ordering the author actually specified.

14. DESIGN_CONSTRAINT: for each DC-n, check the unit, endpoints or observable qualitative rule, affected population, aggregation boundary and operating phase against its rationale. Follow the affected record IDs to their contract, calculation or mechanism and back to the architecture rule. Verify that the cited test, model or review can distinguish compliance from a violation, including the boundary across multiple ports or consumers where the scope is shared. Check resource projections against the current choice and preserve earlier decision history.

Strict but fair; skip nitpicks; «none» for an empty category. The reviewer's table is evidence, not a verdict: the main agent decides each finding.
