"""Render optional capacity comparisons from an already evaluated resource model."""
import math
import re
from html import escape


HEADERS = ("Resource", "Interfaces", "Scenario", "Window", "Offered load", "Sustainable throughput",
           "Unit", "Utilization", "Sources", "Calculation")


def _label(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return escape(" ".join(value.split()), quote=False).replace("|", "&#124;")


def _references(values, field, valid):
    if not isinstance(values, list) or not all(isinstance(i, str) and valid(i) for i in values):
        raise ValueError(f"invalid {field}: {values!r}")
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate reference in {field}: {values!r}")
    return values


def _metric(entry, field, units, assumptions):
    if not isinstance(entry, dict):
        raise ValueError(f"{field} must specify a metric, basis and assumptions")
    name = entry.get("metric")
    if not isinstance(name, str) or name not in units:
        raise ValueError(f"{field} metric {name!r} needs a unit in UNITS")
    _label(units[name], f"UNITS[{name!r}]")
    basis = entry.get("basis")
    if basis not in ("estimated", "measured", "specified"):
        raise ValueError(f"{field} basis must be estimated, measured or specified")
    sources = _references(entry.get("assumptions"), field + " assumptions", assumptions.__contains__)
    if not sources:
        raise ValueError(f"{field} needs at least one source assumption")
    return name, basis, sources


def _result(results, scenario, name):
    value = results[scenario].get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"compute() must return a finite non-negative {name!r} for {scenario}")
    return value


def _source_links(ids):
    return ", ".join(f"[{i}](resource-math.md#{i})" for i in ids)


def capacity_table(entries, results, units, assumptions, limit_ids, calculation_url):
    """One aggregate comparison per resource and selected scenario. No entries produces no block."""
    if not isinstance(entries, list):
        raise ValueError("CAPACITY must be a list of resources")
    if not entries:
        return []
    lines = ["", "### Capacity by resource", "", "| " + " | ".join(HEADERS) + " |",
             "|" + "---|" * len(HEADERS)]
    seen = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("each CAPACITY entry must describe a resource")
        resource = _label(entry.get("resource"), "resource")
        if resource.casefold() in seen:
            raise ValueError(f"{resource}: combine shared demand into one resource entry")
        seen.add(resource.casefold())
        interfaces = _references(entry.get("interfaces", []), "interfaces", lambda i: re.fullmatch(r"(I|X)-\d+", i))
        limits = _references(entry.get("limits", []), "limits", limit_ids.__contains__)
        windows = entry.get("windows")
        if not isinstance(windows, dict) or not windows or windows.keys() - results.keys():
            raise ValueError(f"{resource}: windows must name one or more model scenarios")

        demand, demand_basis, demand_sources = _metric(entry.get("demand"), "demand", units, assumptions)
        sources = "demand " + _source_links(demand_sources)
        names = [_label(demand, "demand metric")]
        supply = entry.get("capacity")
        if supply is not None:
            rate, rate_basis, rate_sources = _metric(supply, "capacity", units, assumptions)
            if units[demand] != units[rate]:
                raise ValueError(f"{resource}: demand and capacity need the same unit in UNITS")
            sources += " · capacity " + _source_links(rate_sources)
            names.append(_label(rate, "capacity metric"))
        if limits:
            sources += " · " + _source_links(limits)
        calculation = "[" + ", ".join(names) + "](" + calculation_url + ")"
        for scenario in results:
            if scenario not in windows:
                continue
            window = _label(windows[scenario], f"{resource} {scenario} window")
            load = _result(results, scenario, demand)
            throughput, utilization = "capacity unknown", "—"
            if supply is not None:
                service = _result(results, scenario, rate)
                throughput = f"{service:.4g} ({rate_basis})"
                utilization = f"{load / service:.2%}" if service else "undefined (zero capacity)"
            cells = (resource, ", ".join(interfaces) or "—", scenario, window, f"{load:.4g} ({demand_basis})",
                     throughput, _label(units[demand], "unit"), utilization, sources, calculation)
            lines.append("| " + " | ".join(cells) + " |")
    return lines
