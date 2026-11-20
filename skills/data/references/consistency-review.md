# Consistency review brief (requirements + resource math + contracts ↔ data)

Give this to a fresh reviewer sub-agent with the paths of `concept.md`, `requirements.md`, `resource-math.md`, `contracts.md` with `contracts/`, `decisions.md` and `data.md`. The reviewer reads all fully, edits nothing, reports in the developer's language, and returns at most 25 rows `type | where (E-/M- id or section) | what is wrong | suggested fix`, most serious first, then a one-paragraph verdict (consistent / minor issues / serious issues). Categories:

1. MISSING_ENTITY: data that a requirement, scenario or contract payload implies (journals, versions, caches, credentials, staging, backups, exports, counters, derived summaries) with no entity.
2. COPY_LEAK: a copy, replica, log excerpt, provider-side retention or derived dataset not listed, or a copy chain that breaks a deletion/retention requirement; a deletion path that cannot reach all copies.
3. VOLUME_WRONG: a size or growth that disagrees with resource-math assumptions or limits, units mixed, a per-item size used as a total, growth missing for an append-only entity, totals over a storage limit.
4. CLASS_MISMATCH: a storage class that does not fit the access pattern, consistency or latency need (a transaction across entities in a store that cannot give it; a hot path on a slow class); or one class forced on everything without reason.
5. OWNERSHIP: two writers for one fact with no rule, an entity nobody writes, a derived entity stored as if it were a source of truth.
6. SENSITIVITY: personal or secret data classified lower than a requirement implies, or exposed through a contract field or a log copy.
7. CONTRADICTION: the data model contradicts a requirement, constraint, concept boundary, contract or non-superseded decision (retention vs history, an invariant vs a contract operation).
8. DESIGN_LEAK: table/index/DDL detail, owning parts (B-n), product or engine choice without a requirement or decision.
9. DIAGRAM_DRIFT: the ER diagram, the catalog and the lifecycle table disagree; a memory region without a limit or a size that does not add up to the RAM limit.

Trace a creation, an update and the end of an instance. In the sensor example, a higher sequence updates the existing reading in °C. Removing its registration ends both lifetimes. A subsequent registration has a fresh ID and its sequence may restart. Check that the logical fields, ER cardinality and copy lifetimes explain what a delayed frame still carries. For each modeled state aspect, verify its source, the condition for every value and the link to its governing mechanism once defined. A derived value should follow from the stated facts after every update. For a referenced memory region, follow its M-n to the contents, size, allocation and exhaustion rule.

Strict but fair; skip nitpicks; «none» for an empty category. The reviewer's table is evidence, not a verdict: the main agent decides each finding.
