# Sensor telemetry v1

x-direction: internal

I-1 carries the registration ID, sequence number and temperature. Sequence numbers increase within an active registration.

## Layout
Registration, sequence and temperature in degrees Celsius, in that order.

## Timing and limits
A receiver can buffer 200 frames. L-1 defines the burst budget.

## Errors
Discard frames for a retired registration or a sequence already superseded. A full buffer drops the incoming frame.
