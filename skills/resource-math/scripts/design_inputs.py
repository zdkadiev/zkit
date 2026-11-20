"""Resolve model inputs from the optional architecture design-constraint catalog."""
import math
import re
from html import escape
from pathlib import Path

from design_constraints import parse_design_constraints


def _endpoint(record, op, unit):
    bound = record.numeric
    if bound is None:
        raise ValueError(f"{record.id} is qualitative and cannot supply a numeric input")
    if unit != bound.unit:
        raise ValueError(f"{record.id} unit mismatch: model expects {unit!r}, architecture declares {bound.unit!r}")

    if bound.exact:
        endpoints = {"=": bound.lower}
    else:
        endpoints = {"<=" if bound.upper_inclusive else "<": bound.upper,
                     ">=" if bound.lower_inclusive else ">": bound.lower}
    value = endpoints.get(op)
    if value is None:
        raise ValueError(f"{record.id} has no {op!r} endpoint in {record.allowed_value!r}")
    return value


def resolve_design_inputs(project, entries, assumptions):
    """Return fixed inputs, provisional assumption aliases and their generated source rows."""
    if not isinstance(entries, dict):
        raise ValueError("DESIGN_INPUTS must map DC-n IDs to endpoint specifications")
    if not entries:
        return {}, {}, []

    root = Path(project)
    owner = next((p for p in (root / "architecture.md", root / "high-level-design.md") if p.is_file()), None)
    if owner:
        records, errors = parse_design_constraints(owner.read_text(encoding="utf-8"))
        if errors:
            raise ValueError(f"{owner.name}: " + "; ".join(errors))

    fixed, provisional = {}, {}
    rows = ["", "**Design inputs**", "", "| Input | Endpoint | Unit | Source |", "|---|---|---|---|"]
    for rid, spec in entries.items():
        if not isinstance(rid, str) or not re.fullmatch(r"DC-\d+", rid) or not isinstance(spec, dict):
            raise ValueError(f"{rid!r} must be a DC-n ID with an endpoint specification")
        if set(spec) - {"op", "unit", "provisional"}:
            raise ValueError(f"{rid} allows only op, unit and provisional")
        op, unit = spec.get("op"), spec.get("unit")
        if op not in ("<", "<=", "=", ">=", ">") or not isinstance(unit, str) or not unit.strip() or "\n" in unit:
            raise ValueError(f"{rid} needs op (<, <=, =, >=, >) and a non-empty unit")
        assumption = spec.get("provisional")
        if "provisional" in spec and (not isinstance(assumption, str) or not re.fullmatch(r"A-\d+", assumption)
                                      or assumption not in assumptions):
            raise ValueError(f"{rid} needs an explicit provisional A-n declared in ASSUMPTIONS")
        if owner:
            if rid not in records:
                raise ValueError(f"unknown {rid} in {owner.name}")
            endpoint = _endpoint(records[rid], op, unit)
            # Report formatting and model arithmetic support finite machine-range numbers.
            value = float(endpoint)
            if not math.isfinite(value) or (value == 0 and endpoint != 0):
                raise ValueError(f"{rid} endpoint cannot be represented by the model")
            fixed[rid] = int(endpoint) if endpoint == endpoint.to_integral_value() else value
            source = f"[{rid}]({owner.name}#{rid})"
            selected = f"{op} {endpoint}"
        else:
            if assumption is None:
                raise ValueError(f"{rid} needs architecture.md or an explicit provisional A-n assumption")
            item = assumptions[assumption]
            if item.get("unit") != unit:
                raise ValueError(f"{rid} provisional {assumption} unit mismatch: expected {unit!r}")
            for scenario in ("best", "expected", "worst"):
                value = item.get(scenario)
                if type(value) not in (int, float) or (isinstance(value, float) and not math.isfinite(value)):
                    raise ValueError(f"{rid} provisional {assumption} needs a finite value for {scenario}")
            provisional[rid] = assumption
            source = f"Provisional [{assumption}](resource-math.md#{assumption})"
            selected = op
        unit_cell = escape(unit, quote=False).replace("|", "&#124;")
        rows.append(f"| `{rid}` | `{selected}` | {unit_cell} | {source} |")
    return fixed, provisional, rows
