# Sample acceptance

> **Counts:** 1 MC
> **Based on:** architecture.md (2026-11-20), contracts.md (2026-11-20), requirements.md (2026-11-20), resource-math.md (2026-11-20).

## Mechanisms

| ID | Part | Mechanism | Kind | Serves | Verified by | Risk |
|---|---|---|---|---|---|---|
| MC-1 | B-2 | Accept samples | state machine | FR-1 | mechanics/model_sample.py | M |

### MC-1 Sample acceptance

**State aspect:** [E-1 / reading availability](data.md#E-1-reading-availability)
**Input:** I-1 · **Memory:** M-1 · **Entity effect:** create or update E-2.

Check the registration before comparing sequence numbers. Removal or restart destroys the instance.

| State | Event | Guard | Next state | Effects |
|---|---|---|---|---|
| awaiting_sample (initial) | sample for this registration | First accepted sample | has_reading | Create E-2 with the incoming sequence and temperature. |
| has_reading | sample for this registration | Incoming sequence exceeds stored sequence | has_reading | Update sequence and temperature together on the existing E-2. |
| has_reading | sample for this registration | Incoming sequence equals or falls below stored sequence | has_reading | Discard frame. Preserve E-2. |

Removal and restart end the registration instance outside this table. This explains the checker warnings about the lack of an outgoing transition from has_reading and the absence of a failure event inside the machine.

## Trivial parts

B-1 emits the input frame.

## Registration and allocation constraints

The [registration boundary model](mechanics/model_registration.py) checks DC-1 using a single registry shared across ports. Its broken variant tracks a separate budget for each port. DC-2 applies throughout sample acceptance. A target-side allocation trace is needed to verify the production handler.

## Internal contracts

| Interface | Spec | What the format must guarantee |
|---|---|---|
| I-1 | contracts/sample.md | Fresh registration and increasing sequence |
