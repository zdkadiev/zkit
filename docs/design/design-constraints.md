# Design constraints

**Status** — Introduced in zkit 0.4.0.

A design constraint is a boundary the designer chooses and other parts of the design rely on. It can be a number, a range, or a qualitative rule. Record it once in an optional **Design constraints** section of `architecture.md`. A project-wide catalog makes these choices discoverable even when their scope is a single controller, port, process, or operating phase.

## Record format

The ID prefix is `DC-n`. Architecture owns its definition and stable anchor. Keep the ID across changes to the value or display name.

| ID | Parameter or rule | Allowed value | Scope | Basis | Applies to | Verification |
|---|---|---|---|---|---|---|
| DC-1 | Active sensor registrations | ≤ 16 registrations | Per controller, across all ports, at every instant | D-1, bounded registration storage | X-1 registration contract, E-1 registration, B-2 controller | Fill the controller across two ports. The next registration is rejected and all existing registrations remain intact. |
| DC-2 | Allocation in the receive handler | Preallocated memory only | Every invocation on B-2 after initialization, including error handling | D-2, bounded allocation time | B-2 controller, MC-1 sample acceptance | Instrument allocations and exercise accepted, duplicate and rejected frames after initialization. Check that the handler performs zero allocations. |

IDs and decisions in the examples are illustrative. For numeric bounds record the unit and inclusive or exclusive endpoints. For qualitative rules state an observable condition. Scope identifies the counted population, aggregation boundary, and operating phase or time window when relevant.

## Ownership and references

- Keep externally imposed constraints in requirements (`C-n`). A design constraint may cite one when it records the specific design choice made to satisfy it.
- Record the rationale and alternatives in a decision (`D-n`). The architecture row owns the current rule. A historical decision can retain its original value.
- Workload assumptions (`A-n`) supply estimates; resource limits (`L-n`) compare calculated demand against a budget. For DC-1, the maximum registration count is the design input, the number of active registrations under expected load can be an assumption, and the resulting memory footprint can be checked against a RAM limit.
- Reference the constraint by ID in each dependent contract, calculation or mechanism. A calculation that uses the chosen bound must obtain it from the canonical record or a projection verified against it. The resource-math stage can run before architecture exists. Once a design choice replaces a provisional sizing input, reconcile the model and rerun the calculation.
- The catalog shows the rule, scope, rationale, affected records and verification. Each affected record links back. A check can verify IDs, references and numeric syntax; the cited test, model or review establishes whether the system satisfies the rule.

## Using a numeric bound in a calculation

The sensor model declares the endpoint and unit it consumes. The resource-math checker supplies its value to `compute(a)` for each scenario.

```python
DESIGN_INPUTS = {"DC-1": {"op": "<=", "unit": "registrations"}}


def compute(a):
    return {"registration_memory": a["DC-1"] * 16}  # 16 bytes per slot
```

Here the slot size and registration count are independent quantities. Open-ended, inclusive and exclusive bounds retain their meaning when a model selects an endpoint. Before architecture exists, a model may explicitly use a documented provisional assumption. [Resource math format](../../skills/resource-math/references/resource-math-template.md#optional-design-inputs)

## Acceptance example

Change DC-1 from 16 to 32 in its owning record. The catalog displays the new bound under the same ID. A sizing calculation for fixed-size registration slots uses 32, and the contract and boundary test still resolve to DC-1. The test accepts the 32nd registration across the controller and rejects the 33rd even when it arrives on a different port. DC-2 remains inspectable and testable independently of numeric parsing. Existing projects can omit the section.
