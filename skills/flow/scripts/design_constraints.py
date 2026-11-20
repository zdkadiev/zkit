"""Read the optional architecture-owned design constraints catalog. Stdlib only."""
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from design_markdown import HEADING, ID_HEADERS, cell_values, content_lines
from ids import IDS, rx


HEADERS = {
    "id": ("ID", *sorted(ID_HEADERS - {"id"})),
    "parameter": ("Parameter or rule", "Параметр или правило"),
    "allowed_value": ("Allowed value", "Допустимое значение"),
    "scope": ("Scope", "Область действия", "Область применения"),
    "basis": ("Basis", "Основание", "Обоснование"),
    "applies_to": ("Applies to", "Применяется к", "Относится к"),
    "verification": ("Verification", "Проверка", "Способ проверки"),
}
HEADER_FIELD = {header.casefold(): field for field, labels in HEADERS.items() for header in labels}
SECTION_TITLES = {"design constraints", "проектные ограничения", "ограничения проектирования"}
PLACEHOLDERS = {"", "-", "–", "—", "…", "...", "tbd", "todo", "n/a", "н/д"}
NUMBER = r"[+-]?(?:\d+(?:\.\d+)?|\.\d+)(?:[eE][+-]?\d+)?"
# Units may be compound, e.g. KiB/s, registrations per controller, %, °C, 1/s.
UNIT_NAME = r"(?:[^\W\d_]|°)\w*"
UNIT_TERM = rf"{UNIT_NAME}(?:-{UNIT_NAME})*(?:\^[+-]?\d+|⁻[⁰¹²³⁴⁵⁶⁷⁸⁹]+)?"
UNIT = rf"(?:[%‰]|1(?=/)|{UNIT_TERM})(?:(?:[·*/.]|\s+){UNIT_TERM})*"
QUANTITY_UNIT = rf"(?:\s+|(?=[%‰°]))(?P<unit>{UNIT})"
SCALAR = re.compile(rf"(?P<op><=|>=|≤|≥|<|>|=)?\s*(?P<n>{NUMBER}){QUANTITY_UNIT}")
INTERVAL = re.compile(rf"(?P<left>\[|\()\s*(?P<lo>{NUMBER})\s*,\s*(?P<hi>{NUMBER})\s*(?P<right>\]|\)){QUANTITY_UNIT}")
NUMERIC_START = re.compile(
    r"^[<>=≤≥≈~±∞+\-\d.\[\(]|^(?:NaN|inf(?:inity)?)\b|"
    r"^(?:up to|at (?:least|most)|more than|less than|no (?:less|more) than|between|"
    r"max(?:imum)?|min(?:imum)?|до|от|не (?:более|менее|больше|меньше)|максимум|минимум)\s+[-+]?\d",
    re.I,
)
RECORD_ID = re.compile(rx(*IDS) + r"\b")


@dataclass(frozen=True)
class NumericBound:
    lower: Optional[Decimal]
    upper: Optional[Decimal]
    lower_inclusive: bool
    upper_inclusive: bool
    unit: str
    exact: bool = False  # Scalar equality and a closed singleton interval have distinct selectors.


@dataclass(frozen=True)
class DesignConstraint:
    id: str
    parameter: str
    allowed_value: str
    scope: str
    basis: str
    applies_to: str
    verification: str
    line: int
    parameter_column: int
    numeric: Optional[NumericBound]


def dc_columns(headers):
    """Map the canonical field names to column indexes in either authoring language."""
    return {HEADER_FIELD[h.casefold().strip()]: i for i, h in enumerate(headers)
            if h.casefold().strip() in HEADER_FIELD}


def _numeric_bound(value):
    text = value.replace("−", "-")
    if match := INTERVAL.fullmatch(text):
        lo, hi = Decimal(match["lo"]), Decimal(match["hi"])
        left, right = match["left"] == "[", match["right"] == "]"
        if lo > hi or (lo == hi and not (left and right)):
            raise ValueError("numeric interval is empty or reversed")
        return NumericBound(lo, hi, left, right, match["unit"])
    if match := SCALAR.fullmatch(text):
        number, op, unit = Decimal(match["n"]), match["op"], match["unit"]
        if op in ("<", "<=", "≤"):
            return NumericBound(None, number, False, op != "<", unit)
        if op in (">", ">=", "≥"):
            return NumericBound(number, None, op != ">", False, unit)
        return NumericBound(number, number, True, True, unit, exact=True)
    if NUMERIC_START.search(text):
        raise ValueError("numeric Allowed value needs a bound or interval with endpoints and a unit, e.g. ≤ 16 registrations or [0, 16) ms")
    return None


def _section_tables(text):
    """Yield each catalog section's heading line and its contiguous Markdown tables."""
    level = 0
    start, tables, table = 0, [], []
    for index, line in content_lines(text.splitlines(), skip_references=True, skip_model=True):
        heading = HEADING.match(line)
        if heading and level and len(heading[1]) <= level:
            yield start, tables
            level = 0
        if heading and not level and heading[2].strip().rstrip("#").rstrip().casefold() in SECTION_TITLES:
            level, start, tables = len(heading[1]), index + 1, []
        if level and re.match(r"^ {0,3}\|", line):
            if not table or table[-1][0] != index:
                table = []
                tables.append(table)
            table.append((index + 1, cell_values(line)))
        else:
            table = []
    if level:
        yield start, tables


def _table_schema(table):
    headers = table[0][1]
    columns = dc_columns(headers)
    missing = [labels[0] for key, labels in HEADERS.items() if key not in columns]
    if missing:
        raise ValueError("missing columns: " + ", ".join(missing))
    if columns["id"] != 0:
        raise ValueError("the ID must be the first column")
    if len(columns) != sum(h.casefold() in HEADER_FIELD for h in headers):
        raise ValueError("duplicate catalog column")
    separator = table[1][1] if len(table) > 1 else []
    if len(separator) != len(headers) or not all(re.fullmatch(r":?-+:?", cell) for cell in separator):
        raise ValueError("missing or malformed Markdown table separator")
    if len(table) == 2:
        raise ValueError("no DC-n rows")
    return columns


def _read_record(number, cells, columns, width):
    if len(cells) != width:
        raise ValueError(f"expected {width} cells, found {len(cells)}")
    fields = {key: cells[i] for key, i in columns.items()}
    empty = [HEADERS[key][0] for key, value in fields.items()
             if value.strip().strip("`*_ ").casefold() in PLACEHOLDERS]
    if empty:
        raise ValueError("empty " + ", ".join(empty))
    if not any(ref != fields["id"] for ref in RECORD_ID.findall(fields["applies_to"])):
        raise ValueError("Applies to must cite an affected record ID")
    value = fields["allowed_value"].strip("`*_ ")
    try:
        numeric = _numeric_bound(value)
    except InvalidOperation as exc:
        raise ValueError("numeric Allowed value is outside the supported decimal range") from exc
    return DesignConstraint(**fields, line=number, parameter_column=columns["parameter"], numeric=numeric)


def parse_design_constraints(text):
    """Return (unambiguous valid records by ID, diagnostics). Lines are one-based."""
    records, seen, errors = {}, {}, []
    for start, tables in _section_tables(text):
        if not tables:
            errors.append(f"Design constraints line {start}: missing catalog table")
        for table in tables:
            line, headers = table[0]
            try:
                columns = _table_schema(table)
            except ValueError as exc:
                errors.append(f"Design constraints line {line}: {exc}")
                continue
            for number, cells in table[2:]:
                rid = cells[0] if cells else ""
                if not re.fullmatch(rx("DC"), rid):
                    errors.append(f"Design constraints line {number}: expected DC-n in the first cell, found {rid!r}")
                    continue
                if rid in seen:
                    errors.append(f"{rid} line {number}: duplicate design constraint {rid}, first declared on line {seen[rid]}")
                    records.pop(rid, None)
                    continue
                seen[rid] = number
                try:
                    records[rid] = _read_record(number, cells, columns, len(headers))
                except ValueError as exc:
                    errors.append(f"{rid} line {number}: {exc}")
    return records, errors
