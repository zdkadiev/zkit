# Contracts index template

Aim for one to two pages plus the spec files in `contracts/`. Sections in this order; drop one only if irrelevant and say so in one line. Products appear only as counterparties or checked candidates.

```markdown
# <Name> — Contracts

> **Links:** [concept](concept.md) · [requirements](requirements.md) · [resource-math](resource-math.md) · [ux](ux.md) (if the step was done) · [decisions](decisions.md)
> **Status:** draft / agreed (agreed only when the clarity gate passes, SKILL.md step 5) · **Date:** <date> · **Based on:** [requirements.md](requirements.md) (<its date>), [resource-math.md](resource-math.md) (<its date>), [ux.md](ux.md) (<its date>, if present)
> **Counts:** <n> X   (the checker compares this with the table)

## 1. Summary
The boundaries in ≤5 sentences: how many, which are consumed and which published, which rest on unverified assumptions, the biggest finding.

## 2. Boundaries
| ID | Boundary | Direction | Paradigm | Protocol | Spec | Counterparty | Limits | Verified | Serves |
|---|---|---|---|---|---|---|---|---|---|
| X-1 | owner API | published | request/response | HTTPS with JSON, owner API v1 | contracts/x-1-owner-api.yaml | owner's browser client | L-1 | — | FR-1, NFR-4 |
| X-2 | model provider | consumed | request/response | HTTPS with JSON, provider API v1 | contracts/x-2-model-provider.yaml | OpenAI-compatible providers | L-2, L-5 | R-1 | FR-5 |

`Protocol` identifies the agreed exchange convention for browsing by protocol. Give a version or transport when compatibility depends on it. The Spec path leads to the authoritative contract. Older indexes may give only a Paradigm. When resource math models this boundary’s bottleneck, include the X-n in its CAPACITY entry.

`Direction`: consumed / published. `Verified`: `R-n` (research report) or the documentation link for consumed contracts, `—` for published, `unverified` otherwise. `Limits`: `L-n` of resource-math. `Spec`: path relative to the project folder.

## 3. Shared conventions
Error model, identifiers, time and money formats, pagination, versioning and compatibility rule, authentication in one line each — what every spec inherits so it is not repeated.

## 4. Findings and consequences
Number the items plainly (`1.`, `2.`); id-like labels (`F-1`, `G-1`) belong to the id registry (`flow/scripts/ids.py`) and fail its check.
- Requirement issues found (a counterparty cannot deliver, a quota below the load) with the decision taken or pending.
- Constraints for the architecture, tagged `→ architecture: …`, `→ data: …`, `→ mechanics: …`.

## 5. Risks, assumptions and open questions
Ranked; every assumed contract has the cheapest way to verify it (a call against the real service, a contract test, a spike for the roadmap).

## 6. Consistency check
Date; `check_contracts.py` result (errors / warnings left and why); verdict of the independent reviewer; what was fixed; what stays open.

## Sources
Numbered URLs; delegated findings link to `[R-n]` reports with their confidence.
```
