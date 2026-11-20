# R-1. Which notation supports drill-down in zkit designs?

**Date** 2026-11-20 · **Decision** How readers move from design context to interface behavior and authoritative details · **Status** Research complete, integration proposed.

## Question

Can a reviewer follow a part into its structure and an exchange into its behavior while zkit keeps ownership of protocols, entities and mechanics in the existing artifacts?

## Findings

| Option | Documented capability | Constraint for zkit | Confidence |
|---|---|---|---|
| Mermaid in Markdown | GitHub renders diagram fences. Mermaid supports flowcharts, sequence, ER and state diagrams. | Each diagram needs its own definition. Click handling depends on renderer security settings. Ordinary adjacent Markdown links offer a route across documents. [GitHub](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/creating-diagrams) · [Mermaid](https://mermaid.js.org/config/usage.html) · [Interaction](https://mermaid.js.org/syntax/flowchart.html#interaction) | High |
| LikeC4 | Custom kinds and scoped views represent domain-specific parts. An edge can carry resource links and open a dynamic view. A static build preserves interactive browsing. | Dynamic steps can be authored independently of modeled relationships. Cross-check interface IDs when generating them. Set detail views to show separate edges when several exchanges share endpoints. [Specification](https://likec4.dev/dsl/specification/) · [Relationships](https://likec4.dev/dsl/relationships/) · [Dynamic views](https://likec4.dev/dsl/views/dynamic/) · [View predicates](https://likec4.dev/dsl/views/predicates/) · [Publishing](https://likec4.dev/guides/publish/) | High |
| Structurizr DSL | Built-in context → container → component navigation, relationship URLs and custom views. Its dynamic diagrams reuse modeled relationships. | A good fit for projects using C4 software abstractions. The static exporter preserves diagram navigation but removes workspace documentation and decisions. Those need separately published destinations. [Navigation](https://docs.structurizr.com/server/diagrams/viewer#navigation) · [Dynamic views](https://docs.structurizr.com/dsl/language#dynamic-view) · [Custom views](https://docs.structurizr.com/dsl/cookbook/custom-view/) · [Static export](https://docs.structurizr.com/export/static-site) | High |
| SysML v2 | Standardized textual and graphical systems models, including requirements, structure and behavior, with a tool API. | Relevant when a project needs engineering-model interchange or analysis. Adopting its semantics throughout zkit would require a mapping from current artifacts and a compatible viewer. [OMG](https://www.omg.org/sysml/sysmlv2/) | High for the standard, unmeasured integration cost |

C4 itself recommends selecting levels according to the reader's needs. Its four structural levels describe software. For general designs, zkit can use the idea of progressive detail with the vocabulary of each project. [C4 diagram guidance](https://c4model.com/diagrams)

## Local probe

I validated a [sensor model](R-1-diagram-navigation/sensor.c4) using LikeC4 1.61.0 and built a hash-routed static site in a temporary directory. In Chrome I opened the overview, used the instrument's navigation control to reach its parts, then used the sample edge's navigation control to open the delayed-frame sequence. The parts and sequence views displayed the UART protocol. The evidence captures the rendered views. [Context](R-1-diagram-navigation/context.png) · [Parts](R-1-diagram-navigation/parts.png) · [Sequence](R-1-diagram-navigation/sequence.png)

To reproduce, run the following from this report's directory with Node compatible with LikeC4 1.61.0. The first command validates the model. The second starts the local viewer.

```sh
npx --yes likec4@1.61.0 validate R-1-diagram-navigation
npx --yes likec4@1.61.0 start R-1-diagram-navigation
```

The probe uses a hand-authored model. It establishes the viewer interaction. Generation from zkit records, repository-host anchor behavior, and integration cost remain unverified. The documentation and local run agreed on the two navigation behaviors tested.

## What it means for zkit

Keep diagram authoring inside the stage that understands the design question. Use LikeC4 as an optional generated reader for structure and exchanges, Mermaid for portable specialist views, and stable Markdown references for exact specifications. The proposal identifies the extra authoring inputs and an acceptance test. [Design proposal](../../../design/diagram-navigation.md)

## Method

Three research briefs covered LikeC4, Structurizr, and Mermaid/SysML. I checked the primary documentation for kinds, edge navigation, dynamic views, static exports and Mermaid interaction restrictions, then exercised the LikeC4 workflow locally. The alternatives were reviewed from their documentation.

## Используется в
<!-- собирается link_docs.py, не править вручную -->
- пока нигде не используется
