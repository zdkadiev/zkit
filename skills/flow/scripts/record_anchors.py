"""Locate published design records by their owner and table schema in zkit Markdown."""
import re
from pathlib import Path

from design_constraints import parse_design_constraints
from design_markdown import ANCHOR, HEADING, ID_HEADERS, INLINE_TOKEN, cell_matches, cell_values, content_lines
from ids import IDS, rx

NAME_COLUMNS = {
    "DC": r"parameter or rule|параметр или правило",
    "B": r"part\b|component\b|часть|компонент\b|responsibility\b|ответственность",
    "I": r"what passes|purpose\b|exchange\b|что переда|что проходит|что и зачем|назначение|обмен",
    "S": r"scenario\b|сценарий",
    "E": r"entity\b|сущность",
    "M": r"region\b|memory region|регион|область|участок",
    "X": r"boundary\b|граница",
    "MC": r"mechanism\b|механизм",
    "A": r"assumption\b|допущение|предположение",
    "L": r"metric\b|метрика|показатель|limit\b|лимит|предел",
}
ENDPOINTS = r"from\b|participants|endpoint|от\b|откуда|отправител|участники|источник"
# Earlier projects also use a generic Name column. Accept it only in the owning
# section or beside properties specific to that kind of declaration.
NAME = re.compile(r"(?:name|title|название|наименование|имя)(?:$| \()")
CATALOGS = {
    "B": (r"parts|building blocks|части|компоненты", r"responsibil|ответственн|owns|владеет"),
    "I": (r"(?:internal )?interfaces|(?:внутренние )?интерфейсы", ENDPOINTS),
    "S": (r"(?:key )?scenarios|(?:ключевые )?сценарии", r"steps|шаги|outcome|итог"),
    "E": (r"entity catalog|catalog of entities|entities|каталог сущност|сущности",
          r"writer|кто пишет|хранил|storage class|sensitivity|чувствительн|meaning|смысл"),
    "M": (r"memory|in-memory|память|стратегия памяти", r"contents|содержим|allocation|выделен|размещен"),
    "X": (r"boundar|external contracts|границ|внешние контракт", r"direction|направлен|counterparty|контрагент"),
    "MC": (r"mechanisms|механизмы", r"kind|тип|verified by|проверен"),
    "A": (r"assumptions|допущени|предположени", r"evidence|достоверност|validation|валидац"),
    "L": (r"limits|ограничени|пределы|лимиты", r"verdict|вердикт|accepted by|принят"),
}
RECORD_HEADING = re.compile(
    r"^ {0,3}#{1,6}\s+([A-Z]+-\d+)(?:[.:]\s*|\s+(?:[-–—]\s+)?)(\S.*?)\s*#*\s*$"
)


def _table_rows(text, *, definitions=False):
    pending = headers = None
    headings = []
    previous = -2
    for index, line in content_lines(text.splitlines(), skip_model=definitions, skip_references=definitions):
        is_table_line = re.match(r"^ {0,3}\|", line)
        if index != previous + 1 or not is_table_line:
            pending = headers = None
        previous = index
        if not is_table_line:
            if heading := HEADING.match(line):
                level = len(heading[1])
                while headings and headings[-1][0] >= level:
                    headings.pop()
                headings.append((level, heading[2].casefold()))
            continue
        cells = cell_values(line)
        if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            headers = pending if pending and len(pending) == len(cells) else None
        elif headers:
            if len(headers) == len(cells):
                yield index + 1, headers, cells, headings
        else:
            pending = [cell.casefold() for cell in cells]


def table_rows(text):
    """Yield one-based line number, headers and values from well-formed Markdown tables."""
    for number, headers, cells, _ in _table_rows(text):
        yield number, headers, cells


def _owner(document_name):
    name = Path(document_name).name
    return "architecture.md" if name == "high-level-design.md" else name


def heading_records(document_name, text):
    """Yield (zero-based line index, record ID, title) for legacy named record headings."""
    owner = _owner(document_name)
    for index, line in content_lines(text.splitlines(), skip_references=True, skip_model=True):
        match = RECORD_HEADING.match(line)
        if match:
            rid, title = match.groups()
            kind = rid.partition("-")[0]
            if kind != "DC" and kind in NAME_COLUMNS and IDS[kind][0] == owner:
                yield index, rid, title


def record_rows(document_name, text):
    """Yield (zero-based line index, record ID, name column) for canonical catalog rows."""
    owner = _owner(document_name)
    if owner == "architecture.md":
        constraints, _ = parse_design_constraints(text)
        for record in constraints.values():
            yield record.line - 1, record.id, record.parameter_column
    for number, headers, cells, headings in _table_rows(text, definitions=True):
        if headers[0] not in ID_HEADERS:
            continue
        rid = cells[0]
        kind = rid.partition("-")[0]
        if kind == "DC" or kind not in NAME_COLUMNS or IDS[kind][0] != owner or not re.fullmatch(r"[A-Z]+-\d+", rid):
            continue
        column = next((i for i, h in enumerate(headers) if re.match(NAME_COLUMNS[kind], h)), None)
        generic = next((i for i, h in enumerate(headers) if NAME.match(h)), None)
        if generic is not None:
            section, signature = CATALOGS[kind]
            if any(re.match(section, title) for _, title in headings) or any(re.match(signature, h) for h in headers):
                column = generic
        # In compact interface catalogs the endpoint cell is the only exchange description.
        if column is None and kind == "I":
            column = next((i for i, h in enumerate(headers) if re.match(ENDPOINTS, h)), None)
        if column is not None and cells[column].strip(" —-"):
            yield number - 1, rid, column


def add_record_anchors(document_name, text):
    """Put one stable target at a record, moving existing targets if its detail moved."""
    destinations = {}
    for index, rid, column in record_rows(document_name, text):
        destinations.setdefault(rid, (index, column))
    # Catalog rows are canonical except for mechanisms, whose detailed heading
    # carries the guards and effects. Older documents can define an ID by heading alone.
    for index, rid, _ in heading_records(document_name, text):
        if rid not in destinations:
            destinations[rid] = index, None
        elif rid.startswith("MC-"):
            row, column = destinations[rid]
            if column is not None and index > row:
                destinations[rid] = index, None
    architecture = _owner(document_name) == "architecture.md"
    if not destinations and not architecture:
        return text

    def managed(anchor_id):
        # DC targets are reserved for valid architecture rows, including after a row is retired.
        return anchor_id in destinations or (architecture and anchor_id and re.fullmatch(rx("DC"), anchor_id))

    lines = text.splitlines(keepends=True)
    visible = content_lines(lines, skip_model=True)
    # Only empty anchor elements of published IDs in table cells or on a line of
    # their own are managed. Code examples and authored aspect keys remain intact.
    for index, line in visible:
        if line.lstrip().startswith("|"):
            lines[index] = INLINE_TOKEN.sub(lambda m: "" if managed(m["anchor_id"]) else m[0], line)
        else:
            standalone = ANCHOR.fullmatch(line.strip())
            if standalone and managed(standalone[1]):
                lines[index] = ""
    for rid, (index, column) in destinations.items():
        anchor = f'<a id="{rid}"></a>'
        line = lines[index]
        if column is None:
            newline = "\r\n" if line.endswith("\r\n") else "\n"
            lines[index] = anchor + newline + line
        else:
            cell = cell_matches(line)[column]
            offset = cell.start(1) + len(cell[1]) - len(cell[1].lstrip())
            lines[index] = line[:offset] + anchor + line[offset:]
    return "".join(lines)
