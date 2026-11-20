# Architecture template

Aim for roughly 3,000-4,500 words. Tables over prose. Use these sections in this order; drop one only if irrelevant and say so in one line. Products only for expensive-to-reverse choices (section 3 and the technology table). No algorithms, field-level schemas, machine-readable internal contracts, libraries — those are `mechanics`.

````markdown
# <Name> — Architecture

> **Links:** [concept](concept.md) · [requirements](requirements.md) · [resource-math](resource-math.md) · [contracts](contracts.md) · [data](data.md) · [decisions](decisions.md)
> **Status:** draft / agreed (agreed only when the clarity gate passes, see SKILL.md step 7) · **Date:** <date> · **Based on:** requirements.md (<date>), resource-math.md (<date>), contracts.md (<date>), data.md (<date>)
> **Counts:** <n> B · <n> I · <n> S · <n> decisions (the checker compares these with the tables, so keep the `<n> B`, `<n> I`, `<n> S` form)

## 1. Summary
The architecture in ≤5 sentences: the chosen style, the 4-8 parts in one line, the decision that shapes everything else, the biggest remaining risk.

## 2. Drivers
What the structure must serve: the architecturally significant requirements, binding resource-math limits, boundaries and entities that need a guardian.
| Driver | Source | Why it shapes the structure |
|---|---|---|
| e.g. External actions only with approval | NFR-9, X-3 | Needs one enforcement point that no agent can bypass |

Quality ranking (top 3-5, in order; the order resolves trade-offs later) and the constraints and load figures the design is sized against.

## 3. Key decisions
One row per fork that is expensive to reverse; the full record is `D-<n>` in decisions.md (options, evidence, why, date).
| Decision | Chosen | Main alternative | Why (one line) | Serves |
|---|---|---|---|---|
| D-<n> | … | … | … | NFR-…, L-… |

Technology under the parts (only choices that are expensive to reverse):
| Concern | Choice | Decision | Price check (resource-math) |
|---|---|---|---|
| e.g. database engine | … | D-<n> | fits L-4 at 120 EUR/month [R-n](research/R-n-slug.md) |

## Design constraints

Optional. Include this section when other records depend on a designer-chosen bound or rule. Keep each ID as the choice evolves.

| ID | Parameter or rule | Allowed value | Scope | Basis | Applies to | Verification |
|---|---|---|---|---|---|---|
| DC-1 | Active registrations | ≤ 16 registrations | Per controller across all ports, at every instant | D-1, bounded storage | B-2, E-1, X-1 | Fill the controller across two ports. Reject the next registration and preserve the existing ones. |
| DC-2 | Receive-handler allocation | Preallocated memory only | B-2 after initialization, including error handling | D-2, bounded allocation time | B-2, MC-1 | Instrument the handler. Accepted, duplicate and rejected frames each produce zero allocations. |

Use the first column for the ID. The Russian heading is `Проектные ограничения`. The Russian headers are `ID`, `Параметр или правило`, `Допустимое значение`, `Область действия`, `Основание`, `Применяется к` and `Проверка`.

Write exact quantities as `16 registrations` or `= 16 registrations`. Use `<`, `≤`, `>` or `≥` for one-sided bounds (`<=` and `>=` also work). Write a range as `[0, 16) ms`, with a bracket for an included endpoint and a parenthesis for an excluded endpoint. Include the unit and use a decimal point for fractions. For a qualitative rule, describe an observable condition in words. Name the counted population, aggregation boundary and applicable phase or time window in Scope. Basis explains the choice or cites its decision. Applies to names affected record IDs. Verification states an action and an observable result or links its test.

Cite the DC-n in the affected records. Keep imposed constraints under C-n in requirements, the decision history under D-n, workload assumptions under A-n and calculated resource limits under L-n. When a model consumes the bound, use the resource-math skill's verified projection and rerun the calculation after changing the constraint.

## 4. Parts
| ID | Part | Parent | Responsibility (one sentence) | Owns (E-n, in-process state) | Faces (X-n) | Limits (L-n) | Build / adopt / buy | Serves |
|---|---|---|---|---|---|---|---|---|
| B-1 | Sampler | — | Publish sensor samples | — | X-1 | L-1 | build | FR-1 |
| B-2 | Controller | — | Accept readings for active registrations | E-1, E-2, M-1 | — | L-1 | build | FR-1 |

Use the optional `Parent` column for containment across cataloged parts. Give the immediate parent's B-n, or `—` for a top-level part. Keep this hierarchy consistent with the scoped Level 3 view. In `Owns`, include the M-n of a memory region the part owns.

Rules: one reason to change per part; every entity E-n has exactly one owner; every boundary X-n is faced by some part; no part is named after a technology.

## 5. C4 diagrams
Mermaid flowcharts in the style of C4. The checker reads the heading to tell the levels apart; keep the words `Level 1`, `Level 2`, `Level 3`.

### Level 1 — System context
People and external systems around the system; external systems carry the contract ids (`X-1`).

### Level 2 — Containers
Parts as nodes (`B1["B-1 Name"]`), databases/queues/other infrastructure as extra nodes, arrows labelled with the interface id (`I-1`), external systems with their `X-n`.

### Level 3 — Components of B-n
For the one or two parts whose inner structure carries a requirement (isolation, approval, money accounting). Say in one line why this part. Identify the containing B-n explicitly in the heading or subgraph. Keep links to the part, its interfaces and the related scenario beside the diagram. The flow skill can generate a linked inventory and optional interactive views from the records.

## 6. Interfaces
| ID | From → to | What passes and why | Style (sync / async / event) | Protocol | Entity effects | Resources | Delivery semantics | Serves |
|---|---|---|---|---|---|---|---|---|
| I-1 | B-1 (publisher) → B-2 (recipient) | Deliver registration ID, sequence and temperature to refresh the display | event | Sensor telemetry v1 over UART | B-2 reads E-1 and updates E-2 on acceptance | M-1, A-1, L-1 | Loss, duplicates and delayed frames are possible | FR-1 |

Give each independently specified exchange one I-n. List additional subscribers to the same contract in the endpoint cell and attribute each effect to its participant. Exchanges between the same parts with different guarantees can have distinct IDs. Describe inputs and outputs in the exchange cell. State the ordering, loss, duplication or completion guarantees that matter in Delivery semantics.

Every row needs `Protocol` and `Entity effects` (Russian headers `Протокол` and `Влияние на сущности`). Name the protocol, version or transport needed for compatibility. For custom frames, in-process calls and human handoffs, describe the agreed convention or link its specification. For each modeled effect, give the participant B-n, operation and E-n. A stateless exchange uses `none` (`нет`). Once a governing mechanism exists, add its MC-n to the effect and put any detailed I-n spec in the mechanics internal-contracts table. Architecture can describe the effect before mechanics exists.

The optional `Resources` column cites affected memory regions M-n and applicable assumptions A-n and limits L-n. Put load, capacity, units and the calculation in resource math. When a modeled resource serves several interfaces, add their IDs to that resource’s CAPACITY entry so the reader shows the combined demand once. External operations link to their X-n record in contracts.

## 7. Key scenarios
3-6 walk-throughs, step by step through parts and interfaces. At least one is the main flow and two are failure or hard-requirement flows (restart in the middle of an external action, quota exhausted, a hostile input, a part down, a deletion request reaching every copy).
| ID | Scenario | Steps (B-/I- ids) | Alternate path | Outcome against requirements | Gaps found |
|---|---|---|---|---|---|
| S-1 | Deliver a sample | B-1 → I-1 → B-2 | — | B-2 displays the newest accepted sample for FR-1 | none |

For a sequence view, give each ordered step as sender B-n → I-n → recipient B-n. A chain may continue from the previous recipient. Separate independent complete triples with a semicolon. The optional `Alternate path` holds the complete ordered exchanges for a selected alternate case. Give a distinct failure scenario its own S-n where it has its own outcome. Keep the branching condition and observable outcome with the scenario. Describe an unspecified order in prose until it is known.

## 8. Cross-cutting concerns
Security and secrets, reliability and recovery, observability, cost control, data isolation, deployment shape — one short paragraph each, pointing to the parts and requirements that carry it; the depth comes in `resilience`. Skipped ones listed with the reason.

## 9. Traceability
| Requirement | Covered by |
|---|---|
| FR-1 | B-…, I-…, D-… |
Every Must requirement appears, grouped by theme with ranges (`FR-13…FR-15`) rather than one row each. Requirements with no covering part are listed as **uncovered** with the reason; parts that serve no requirement as **orphans**, justified or cut.

## 10. Reconciliation with earlier steps
What the architecture changed or found in earlier documents: contracts revised, resource-math assumptions or limits adjusted, data entities moved, requirements questioned — each with the decision or the pending question.

## 11. Risks, assumptions and open questions
Ranked. Architectural assumptions that carry a Must requirement each get the cheapest way to validate (a spike or measurement; it becomes a task at the roadmap stage), forks not yet decided.

## 12. Deferred
One line per detail that came up, tagged with the target stage (`→ mechanics: …`, `→ resilience: …`, `→ roadmap: …`).

## 13. Consistency check
Date; `check_architecture.py` result (errors / warnings left and why); verdict of the independent reviewer; what was fixed; what stays open.

## Sources
Numbered URLs; delegated findings link to `[R-n]` reports with their confidence.
````
