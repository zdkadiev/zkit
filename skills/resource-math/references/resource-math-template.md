# Resource math template

Aim for roughly 1,500-3,000 words around the model, at most ~20 assumptions. Tables over prose. Sections in this order; drop one only if irrelevant and say so in one line. Products appear only as sources of numbers. No architecture, no data formats, no algorithms.

```markdown
# <Name> — Resource math

> **Links:** [concept](concept.md) · [requirements](requirements.md) · [decisions](decisions.md) · [model](resource-math/model.py)
> **Status:** draft / agreed (agreed only when the clarity gate passes, SKILL.md step 6) · **Date:** <date> · **Based on:** [requirements.md](requirements.md) (<requirements' own date>)
> **Verdict:** fits / fits with changes / does not fit
> **Counts:** <n> A · <n> L   (the checker compares these with resource-math/model.py)

## 1. Summary
The verdict in ≤5 sentences: what was tested, does it fit in the expected and the worst scenario, the 2-3 assumptions that decide it, what the design must respect.

## 2. Workload
The units that arrive (users, organizations, agents, tasks, messages, frames, samples), how many, how often, how bursty, how they combine. Where each figure comes from (requirement, concept §n, assumption A-n).

## 3. Resources in play
| Resource | Binds? | Why / why not |
|---|---|---|
| e.g. memory per active environment | yes | sets servers per organization, therefore cost |

## 4. Assumptions
| ID | Assumption | Unit | Best | Expected | Worst | Evidence | Source | Validation |
|---|---|---|---|---|---|---|---|---|
| A-1 | … | … | … | … | … | known / measured / assumed | requirement id, [R-n](research/R-n-slug.md), "developer" | cheapest check for an *assumed* one (measurement, spike, pilot) |

`best` is the value most favourable for the limits, `worst` the least favourable. Values here must equal resource-math/model.py (the checker compares ids and counts).

## 5. Model
Formulas in words, one line each (the code is in `resource-math/model.py`; comment names the resource). Then the generated block - never type numbers into it, run `check_resource_math.py <project-dir> --update`:

<!-- model:begin -->
<!-- model:end -->

## 6. Limits and verdicts
| ID | Limit | Requirement | Verdict (expected / worst) | Accepted by |
|---|---|---|---|---|
| L-1 | … | NFR-… / C-… | fits / fits with changes / does not fit | `D-<n>` if it fails and the failure is accepted, else — |

Numeric Must requirements the math cannot test are listed here as **not resource-bound** with the reason.

## 7. Consequences for the design
Ceilings and unit costs the architecture must respect (per part, per unit, per call), what to measure first and why (the largest uncertainty × the verdict), where the first spike belongs. Constraints, not a design. Each line tagged `→ architecture: …`, `→ contracts: …`, `→ data: …`, `→ roadmap: spike …`.

## 8. Risks, assumptions and open questions
Ranked. Requirements issues found by the math (impossible, conflicting, missing) with the decision taken or pending.

## 9. Consistency check
Date; `check_resource_math.py` result (errors / warnings left and why); verdict of the independent reviewer; what was fixed; what stays open.

## Sources
Numbered URLs; delegated findings link to `[R-n]` reports with their confidence.
```

### Optional design inputs

For a calculation that reserves storage per registration, declare the registration bound once in the architecture catalog. Give the model its identifier, endpoint operator and unit. This example uses a 64-byte slot.

```python
DESIGN_INPUTS = {"DC-1": {"op": "<=", "unit": "registrations"}}

def compute(a):
    return {"slot_memory": a["DC-1"] * 64}
```

The checker reads the allowed value from `architecture.md` (or the legacy `high-level-design.md`). All scenarios receive the same resolved endpoint. The generated **Design inputs** table links to its declaration. After a catalog edit, run the checker with `--update` to regenerate the results and review the limit verdicts.

Use `=` for an exact value, `<` or `<=` to select an upper endpoint, and `>` or `>=` to select a lower endpoint. The operator must match the endpoint’s inclusivity and the units must match exactly. For an exclusive endpoint, `compute` receives the boundary itself. For example, a discrete count strictly below 10 has a maximum of 9. Express any such conversion in the formula. Qualitative rules belong in the verification of their affected records.

Before architecture exists, models can use `ASSUMPTIONS` directly. To prepare a calculation for a planned constraint, add `"provisional": "A-3"` to its entry and document A-3 with the same unit and its scenario values. Each scenario and sensitivity run then uses that assumption and the report labels the source **Provisional**. Once an architecture document exists, the checker requires the declared DC-n to resolve. Remove a superseded provisional assumption from the model and its assumptions table if it has no further use.

### Optional capacity comparisons

When throughput matters, add `CAPACITY` to the existing model. Its entries identify results of `compute(a)`. The checker generates **Capacity by resource** inside the model block. The design inventory can then display the same figures for each listed interface. A resource can be named before the architecture exists. Add its interface IDs once their owners define them.

```python
# compute(a) returns arrivals_total and receiver_rate, both in frames/s in UNITS.
CAPACITY = [{
    "resource": "B-2 receiver",
    "interfaces": ["I-1", "I-2"],
    "demand": {"metric": "arrivals_total", "basis": "estimated", "assumptions": ["A-1", "A-2"]},
    "capacity": {"metric": "receiver_rate", "basis": "measured", "assumptions": ["A-3"]},
    "windows": {"expected": "steady operation, 1 s", "worst": "one-second burst"},
    "limits": ["L-1"],
}]
```

- Declare one entry per limiting resource. For shared receivers, links or quotas, sum the simultaneous contributors in `compute(a)` and list the interfaces that consume that total. The displayed utilization is combined offered load divided by sustainable throughput for that resource. Label separate resources when an exchange traverses several bottlenecks.
- Give each metric its evidence basis. Use `measured` for observations under the stated conditions, `specified` for a documented rating, and `estimated` for a workload assumption or extrapolation. Cite the model assumptions that carry the original measurement, specification or validation plan. Include any applicable limit IDs. The source tables hold the evidence and the calculation link names the metrics returned by the model.
- Use matching units for demand and service and state the time window for each applicable model scenario (`best`, `expected`, `worst`). Convert values to comparable rates in the model. For a burst, document the assumptions about arrivals and service over that window. For example, a uniform 1,200 frames/s for one second with continuous service at 1,000 frames/s adds 200 frames to an initially empty queue.
- Include demand even if sustainable throughput is unknown. Omit `capacity` in that case. The reader shows **capacity unknown** and leaves utilization blank. A known zero service rate is a separate model result.
- Omit `interfaces` until the project declares applicable I-n or X-n records. Omit `limits` when the model has no corresponding requirement limit. Omit the entire `CAPACITY` list for models that do not compare resource throughput.
