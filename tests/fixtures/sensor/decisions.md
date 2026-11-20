# Design decisions

<a id="D-1"></a>
### D-1: Share the registration budget across all ports

Static storage makes the memory budget predictable. The controller enforces the DC-1 bound on its registry.

<a id="D-2"></a>
### D-2: Allocate the receive ring before polling

The receive handler has a bounded execution-time budget. DC-2 applies on all paths through the handler.
