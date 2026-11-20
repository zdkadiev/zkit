"""Check the active registration limit across two input ports."""
from pathlib import Path

from design_constraints import parse_design_constraints


def check_boundary(limit, per_port=False):
    active = {}
    for index in range(limit + 1):
        port = index % 2
        used = sum(owner == port for owner in active.values()) if per_port else len(active)
        if used < limit:
            active[index] = port
    return [] if list(active) == list(range(limit)) else ["Shared registration limit violated"]


def run(broken=False):
    architecture = Path(__file__).resolve().parents[1] / "architecture.md"
    constraints, errors = parse_design_constraints(architecture.read_text(encoding="utf-8"))
    if errors:
        raise ValueError(", ".join(errors))
    bound = constraints["DC-1"].numeric
    if bound.unit != "registrations" or not bound.upper_inclusive or bound.upper != int(bound.upper):
        raise ValueError("DC-1 must supply an inclusive registration count")
    return check_boundary(int(bound.upper), per_port=broken)
