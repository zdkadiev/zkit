# Registration procedure

Assign a fresh registration ID on activation. Retire it on removal or restart.

## Layout
An operator supplies the sensor identity and receives a fresh registration ID.

## Timing and limits
All ports draw on the same [controller registration limit](../architecture.md#DC-1).

## Errors
A full registry rejects the new registration and preserves the active set.
