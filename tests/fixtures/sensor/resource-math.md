# Instrument resource math

> **Verdict:** fits
> **Counts:** 2 A · 1 L
> **Based on:** requirements.md (2026-11-20).

## Assumptions

| ID | Assumption | Unit | Best | Expected | Worst | Evidence | Source | Validation |
|---|---|---|---|---|---|---|---|---|
| A-1 | Offered frames | frames/s | 400 | 800 | 1200 | assumed | Illustrative traffic profile | Trace arrivals |
| A-2 | Receiver rate | frames/s | 1000 | 1000 | 1000 | assumed | Illustrative processing budget | Benchmark receiver |

## Model

<!-- model:begin -->
**Results**

| Result | Unit | Best | Expected | Worst |
|---|---|---|---|---|
| arrivals | frames/s | 400 | 800 | 1200 |
| service | frames/s | 1000 | 1000 | 1000 |
| backlog | frames | 0 | 0 | 200 |
| registration_memory | B | 256 | 256 | 256 |

**Design inputs**

| Input | Endpoint | Unit | Source |
|---|---|---|---|
| `DC-1` | `<= 16` | registrations | [DC-1](architecture.md#DC-1) |

[Sizing model](resource-math/model.py)

**Limits**

| ID | Metric | Limit | Best | Expected | Worst |
|---|---|---|---|---|---|
| L-1 | backlog | <= 200 | 0 ✓ | 0 ✓ | 200 ✓ |

**Sensitivity** (one assumption at its worst value, others expected; the limit it moves most)

| Assumption | Limit | Change of the metric |
|---|---|---|

### Capacity by resource

| Resource | Interfaces | Scenario | Window | Offered load | Sustainable throughput | Unit | Utilization | Sources | Calculation |
|---|---|---|---|---|---|---|---|---|---|
| B-2 receiver | I-1 | best | quiet, 1 s | 400 (estimated) | 1000 (estimated) | frames/s | 40.00% | demand [A-1](resource-math.md#A-1) · capacity [A-2](resource-math.md#A-2) · [L-1](resource-math.md#L-1) | [arrivals, service](resource-math/model.py) |
| B-2 receiver | I-1 | expected | normal, 1 s | 800 (estimated) | 1000 (estimated) | frames/s | 80.00% | demand [A-1](resource-math.md#A-1) · capacity [A-2](resource-math.md#A-2) · [L-1](resource-math.md#L-1) | [arrivals, service](resource-math/model.py) |
| B-2 receiver | I-1 | worst | burst, 1 s | 1200 (estimated) | 1000 (estimated) | frames/s | 120.00% | demand [A-1](resource-math.md#A-1) · capacity [A-2](resource-math.md#A-2) · [L-1](resource-math.md#L-1) | [arrivals, service](resource-math/model.py) |
<!-- model:end -->

## Limits and verdicts

| ID | Limit | Requirement | Verdict (expected / worst) | Accepted by |
|---|---|---|---|---|
| L-1 | Backlog after one second at constant demand | FR-1 | fits / fits | — |
