# Internal interface record

Format used by zkit 0.3.0. This specification extends the architecture template's internal interface table with a required Protocol column and explicit entity effects. The example uses English headers.

## Location and identity

An internal interface occupies one row in the Interfaces section of a project's `architecture.md`. Its ID is the reference used by architecture scenarios, C4 diagram edges, and detailed mechanics contracts. External boundaries use the contracts step's `X-n` records.

**Interface identity.** Give an independently specified exchange one ID. List the participant roles in the endpoint cell. A second subscriber to the same event contract shares the ID. A separately negotiated exchange with different guarantees gets its own ID, even if it carries the same data. For fan-out, record any recipient-specific entity effects against that recipient.

## Fields

| Field | Meaning |
|---|---|
| ID | An interface identifier of the form `I-n`, unique in the architecture document. Preserve the identifier when revising the same interface. |
| From → to | Identify the participating parts by their `B-n` IDs in interaction order. For a call, give caller then callee. For an event, give publisher then recipient. Describe any return value in the next column. |
| What passes and why | Name the operation or exchange, what it carries, and its purpose. Name the information on the interface. Put its consequences in Entity effects. |
| Style (sync / async / event) | Describe how the parties interact. An event may also be asynchronous. The existing template gives examples and the checker treats this cell as text. |
| Protocol | Required for every interface. Name the agreed rules of exchange, including the version or underlying transport when compatibility depends on it. For a custom protocol, name it and describe the exchange briefly or reference its specification. For an in-process call or human handoff, identify the calling or handoff convention. |
| Entity effects | For each participating part that reads or changes modeled data, name the part, entity ID and operation. Use “none” for a stateless exchange. Cite the mechanics rule once it exists. |
| Delivery semantics | State the guarantees the design relies on, such as ordering, permitted loss, duplicate handling, or completion. When the design requires no particular guarantee, say so explicitly. |
| Serves | Reference the functional requirement, non-functional requirement, or constraint that motivates the interface. |

## Example

FR-1 requires the instrument to display the latest accepted temperature for each active registration. B-1 is the sampler. B-2 is the controller and owns E-1 (registration) and E-2 (current reading).

| ID | From → to | What passes and why | Style (sync / async / event) | Protocol | Entity effects | Delivery semantics | Serves |
|---|---|---|---|---|---|---|---|
| I-1 | B-1 (publisher) → B-2 (recipient) | Send registration ID, sample sequence and temperature in °C to refresh the display. | event | Sensor telemetry v1 over UART, one unacknowledged frame per sample. | B-2 reads E-1 and creates or updates E-2 on acceptance under MC-1. | Loss is permitted. Duplicate and delayed samples may arrive. | FR-1 |

The [entity definitions and sample acceptance rule](data-model-format.md#mc-1-sample-acceptance) show what happens when this interface delivers a first sample, a newer sample, or a delayed sample from a previous registration.

## Validation and lifecycle

Protocol and Entity effects are required by the current format. Version 0.3.0 emits both fields in the template. The checker warns on legacy tables missing both columns and rejects partially upgraded tables or empty required cells.

The architecture checker rejects duplicate interface IDs, fewer than two part references in the endpoint cell, and references to undefined parts. It warns when an interface cites no requirement or constraint. When requirements are available, it rejects an unknown cited requirement or constraint. The checker also resolves interface references in scenarios and diagram edges.

The row describes the exchange during architecture design. At the mechanics stage, an interface that crosses a process or trust boundary or carries a requirement receives a detailed specification under `contracts/`, referenced by the same interface ID and marked with `x-direction: internal`. For the example, a detailed frame specification could define how the reading and sequence number are encoded.

The descriptions of direction, purpose, interaction style, and delivery guarantees above are authoring guidance. The current endpoint check counts and resolves part references. It does not verify their roles or the meaning of the exchange.
