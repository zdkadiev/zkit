# Mechanics template

Aim for roughly 2,500-4,500 words plus the executable models. Tables over prose. Sections in this order; drop one only if irrelevant and say so in one line. No production code, no failure-handling policy (resilience), no tasks (roadmap).

````markdown
# <Name> — Mechanics

> **Links:** [concept](concept.md) · [requirements](requirements.md) · [resource-math](resource-math.md) · [contracts](contracts.md) · [data](data.md) · [architecture](architecture.md) · [decisions](decisions.md)
> **Status:** draft / agreed (agreed only when the clarity gate passes, SKILL.md step 6) · **Date:** <date> · **Based on:** requirements.md (<date>), resource-math.md (<date>), contracts.md (<date>), architecture.md (<date>)
> **Counts:** <n> MC   (the checker compares this with the mechanism table)

## 1. Summary
The mechanics in ≤5 sentences: how many mechanisms, which are high risk, what the executable models found, the biggest remaining risk.

## 2. Mechanisms
| ID | Part | Mechanism | Kind | Serves | Verified by | Risk |
|---|---|---|---|---|---|---|
| MC-1 | B-2 | Sample acceptance | state machine | FR-1 | review | M |
| MC-2 | B-3 | Quota reservation before a model call | algorithm | NFR-1, L-7 | mechanics/model_quota.py | H |

`Kind`: state machine / algorithm / protocol / concurrency / timing / memory / format. `Verified by`: an executable model path, `review` (the independent reviewer) or a test idea for the roadmap. `Risk`: H (a violated invariant breaks money, isolation, exactly-once or a deadline) / M / L.

### MC-1 Sample acceptance
**Owner:** [B-2](architecture.md#B-2) · **Input:** [I-1](architecture.md#I-1) · **Subject:** [E-1 / reading availability](data.md#E-1-reading-availability)

One machine instance exists per active registration. Check for a live registration before looking up its [current reading](data.md#E-2) in [M-1](data.md#M-1). Discard frames for retired registrations. Evaluate the guard and apply the effect atomically relative to other samples and registration removal.

| State | Event | Guard | Next state | Effects |
|---|---|---|---|---|
| awaiting_sample (initial) | sample for this registration | First accepted sample | has_reading | Create E-2 with the received sequence and temperature. |
| has_reading | sample for this registration | Incoming sequence exceeds stored sequence | has_reading | Update sequence and temperature together. |
| has_reading | sample for this registration | Incoming sequence is equal to or below stored sequence | has_reading | Discard the frame and preserve the current reading. |

Removal destroys the instance and deletes its E-2. After shutdown a fresh registration begins in `awaiting_sample`. This machine has no timeout. Its final live state can only self-transition, since removal happens outside the machine. Record this boundary when explaining the checker's dead-end and missing-failure-event warnings.

Start each table with its initial state. Mark terminal states with `(final)`. Include timeout, crash/restart, duplicate delivery and cancel events where applicable. A state diagram, when useful, follows the same table and links to this MC-n and the exact entity/aspect. A machine that governs a transient procedure may say so and describe the instance lifetime without naming an entity state.

### MC-2 Quota reservation (B-3)
Purpose and the requirement it serves, the rule in pseudocode or formulas, **invariants** (`reserved + spent ≤ quota at every instant`), the interleavings and failures that threaten it, limits from resource-math it must respect, and its input interfaces.

## 3. Trivial parts
One line per part with no mechanism of its own, saying why: `B-1: a form over the owner API, no state.`

## 4. Internal contracts
Interfaces that cross a process or trust boundary or carry a requirement, specified in `contracts/` with boundary id `I-n` and `x-direction: internal` (skeletons in the `contracts` skill):
| Interface | Spec | What the format must guarantee |
|---|---|---|
| I-17 | contracts/i-17-signed-context.yaml | signed, expiring, carries account, organization, role, plan status |

## 5. Timing, memory and concurrency rules
Cross-mechanism rules that no single section owns: lock order, who owns which timeout, priorities and interrupt levels, buffer and pool sizes against the resource-math limits, clock assumptions. Each rule names its owner and the limit it serves.

## 6. Executable checks
For each model in `mechanics/`: what it enumerates (actors, interleavings, crash points), the invariants it asserts, what the `broken` variant switches off, and what it found (including violations fixed in the design).

## 7. Reconciliation with earlier steps
What the mechanics changed or found in earlier documents (architecture parts or interfaces moved, contracts revised, resource-math assumptions adjusted, requirements questioned) with the decision or the pending question.

## 8. Risks, assumptions and open questions
Ranked; every assumed mechanism has the cheapest way to validate it (a model, a spike, a measurement; it becomes a roadmap task).

## 9. Deferred
One line per detail that came up, tagged with the target stage (`→ resilience: …`, `→ roadmap: spike …`).

## 10. Consistency check
Date; `check_mechanics.py` result (errors / warnings left and why, models run and their outcome); verdict of the independent reviewer; what was fixed; what stays open.

## Sources
Numbered URLs; delegated findings link to `[R-n]` reports with their confidence.
````
