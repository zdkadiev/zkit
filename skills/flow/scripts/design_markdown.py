"""Markdown syntax shared by design record publication and validation."""
import re

ID_HEADERS = {"id", "ид", "код", "идентификатор"}
ANCHOR = re.compile(r"""<a\s+id=["'](?P<anchor_id>[^"']+)["']\s*></a>""", re.I)
# Inline code can quote the literal anchor markup. Only real HTML elements count.
INLINE_CODE = r"(?<!`)(?P<ticks>`+)(?!`).*?(?<!`)(?P=ticks)(?!`)"
INLINE_TOKEN = re.compile(INLINE_CODE + "|" + ANCHOR.pattern, ANCHOR.flags)
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
CELL = re.compile(r"\|((?:\\.|[^|\\\r\n])*)")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(?:\d+(?:\.\d+)*[.)]?\s+)?(.+)")
REFERENCE_SECTION = re.compile(
    r"traceability|трассир|прослеживаем|logical fields|логические поля|lifecycle|жизненный цикл|"
    r"entity states|состояния сущност|reconciliation|сверка", re.I
)


def content_lines(lines, *, skip_model=False, skip_references=False):
    """Yield zero-based indexes and text outside fenced examples and HTML comment blocks."""
    closing = None
    in_model = in_comment = False
    reference_level = None
    for index, line in enumerate(lines):
        match = FENCE.match(line)
        if closing:
            if match and match[1].startswith(closing) and not match[2].strip():
                closing = None
            continue
        if in_comment:
            if "-->" in line:
                in_comment = False
            continue
        if line.lstrip().startswith("<!--"):
            in_comment = "-->" not in line
            if skip_model and line.strip() == "<!-- model:begin -->":
                in_model = True
            elif line.strip() == "<!-- model:end -->":
                in_model = False
            continue
        if match:
            closing = match[1]
            continue
        if skip_references and (heading := HEADING.match(line)):
            level = len(heading[1])
            if reference_level is not None and level <= reference_level:
                reference_level = None
            if reference_level is None and REFERENCE_SECTION.match(heading[2]):
                reference_level = level
        if not in_model and reference_level is None:
            yield index, line


def cell_matches(line):
    cells = list(CELL.finditer(line.rstrip()))
    # An optional trailing pipe terminates the last cell.
    if cells and cells[-1][1] == "" and cells[-1].end() == len(line.rstrip()):
        cells.pop()
    return cells


def cell_values(line):
    """Read the displayed cell values, leaving quoted anchor examples intact."""
    return [INLINE_TOKEN.sub(lambda m: m[0] if m["ticks"] else "", match[1]).strip()
            for match in cell_matches(line)]
