# Navigating a zkit design from context to detail

**Implemented in zkit 0.3.0.** Readers should be able to follow either a part or an interaction. On a part, show what it contains and the boundaries it touches. On an interaction, show a scenario and provide links to its protocol, affected data, and behavior. Link every detailed view back to the overview or owning record. The [research and local probe](../zkit/design-views/research/R-1-diagram-navigation.md) compare four approaches.

## Views in the existing design flow

| Reader's question | View in the design document | Owner and drill-down destination |
|---|---|---|
| Where is the boundary? | Context with people, neighboring systems or devices, and the designed system | Architecture. Open the system to see its parts, or an external exchange to see its X-n boundary contract. |
| What is inside, and how do parts interact? | Part/decomposition diagram with interfaces on edges. A complex or risky part can have a scoped view. | Architecture owns B-n, I-n, participant roles and protocols. Open a part for its internals or an edge for its exchange. |
| What happens in a specific case? | Sequence diagram for a selected S-n, including an alternate or failure path where it changes the outcome | Architecture owns the scenario; mechanics supplies guards and effects. Open I-n for the contract or MC-n for the decision rule. |
| What fact is affected? | ER diagram when identity, ownership or cardinality matters | Data owns E-n. Open the entity for logical fields, units, relationships and retention. |
| What changes state, and why? | State diagram for a requirement-bearing entity aspect | Derive states and transitions from the mechanics table. Link back to the data vocabulary and the exact guard/effect row or mechanism. |
| Where can a failure occur? | A deployment or physical topology view when placement or failure domains affect a requirement | Architecture and resilience link existing parts to the relevant failure or recovery scenario. Introduce this view only where it answers a concrete question. |

For a human workflow the same structure can show teams, handoffs and decision rules. For an embedded design it can show devices, signals and timing constraints. Use the project's domain language for captions.

## Inventory and capacity

Provide a project-wide inventory and a part-scoped view. The inventory includes every declared entity (E-n), memory region (M-n), internal interface (I-n) and external boundary (X-n), including records omitted from the current diagram. Group interfaces by protocol and link each usage to its actual contract. From an entity or region, show the owning part and known readers and writers. From an interface, show its participants, protocol, affected entities and regions, and the governing mechanism when defined.

For a selected interface or shared resource, show offered load and sustainable throughput in comparable units, with the workload window, scenario and limiting resource. Link the figures to assumptions (A-n), limits (L-n) and the calculation in resource math. Keep measured, specified and estimated values distinguishable. Show an explicit “capacity unknown” if only demand is known. For shared capacity, compare combined demand with the resource limit once. [Resource math template](../../skills/resource-math/references/resource-math-template.md)

For example, assume an aggregate arrival rate of 800 frames/s normally and 1,200 frames/s during a one-second burst. If the receiver can sustain an estimated 1,000 frames/s, its expected utilization is 80%. During the burst, 200 frames need buffering to avoid loss, assuming an initially empty queue, uniform arrivals and continuous service. This is a receiver estimate. A slower link could further limit end-to-end throughput.

Acceptance: a reader can find an interface from the inventory without traversing a diagram, open its protocol, find the data and memory it affects, and reproduce its expected and burst estimates from their sources. Updating a workload assumption refreshes all views of the same estimate.

## How the two representations fit together

Markdown records remain authoritative. Give each referenced record a stable anchor derived from its zkit ID, scoped to its project. For a state aspect, use the entity ID plus a stable aspect key. Multiple references to an ID link to the owning record. Display names can change without breaking navigation.

Keep Mermaid diagrams and adjacent links in the Markdown reading path. Offer an optional local LikeC4 build for the overview, parts and scenarios. Generate the model from authoritative records. Keep authored view choices small: scope, included IDs, display order and what a click opens. Renderers may need different names for a node; preserve the zkit ID for lookup. A fan-out event keeps one interface ID across its recipients. If two interfaces share endpoints, make each selectable in the detail view.

**What the existing tables cannot supply.** A flat parts catalog cannot determine containment, and a list of exchanges cannot determine when they happen. Reuse hierarchy from an existing level-3 diagram when it is explicit. Otherwise the author specifies parent and scope. Reuse ordered scenario steps where they name the participants and exchange unambiguously. Ask for missing branch or ordering information only when the author chooses to draw that scenario. Keep exact protocol fields, cardinalities and transition guards with the existing contracts, ER model and mechanics tables.

## Pilot and decision

Use the existing sensor design. A reader should be able to open the instrument, find B-2, follow I-1 to the delayed-frame sequence, open E-2 and MC-1, and explain why registration R7 with sequence 99 cannot overwrite R8 with sequence 3. The plugin generates these views from project documents. Its local preview serves diagrams, the complete inventory and linked source records on the same loopback address. [Interface](internal-interface-format.md#example) · [Entity](data-model-format.md#logical-fields) · [Acceptance rule](data-model-format.md#mc-1-sample-acceptance)

Before adopting a renderer, test the same route from repository Markdown and the interactive preview. Rename a part, change the protocol once, and add a second exchange between the same participants. Both readers should show the new facts, preserve link targets and distinguish the two interfaces. Accept the optional build if it meets those checks and authors can maintain the design in one place. Otherwise ship linked Markdown views and revisit the interactive build when a concrete navigation need remains.

See the [browse workflow](../../skills/flow/SKILL.md#browse-a-design) for the installed commands and optional preview dependencies.

## Sources

- [R-1, comparison, primary sources and reproducible sensor model](../zkit/design-views/research/R-1-diagram-navigation.md)
