"""Project ER and state views from authored Mermaid fences and mechanics tables."""
from itertools import groupby
from pathlib import Path
import re


FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+)$")
COLUMN = {
    "state": r"state|состояние",
    "event": r"event|событие",
    "guard": r"guard|условие\b.*|защитное условие",
    "target": r"next state|следующ\w*(?: состояние)?|новое состояние",
    "effect": r"effects?|actions?|эффект\w*|действи\w*|побочные эффекты",
}


def blocks(text):
    """Return ordinary lines and complete fences, keeping longer fences around examples intact."""
    lines = iter(text.splitlines())
    for line in lines:
        match = FENCE.match(line)
        if not match:
            yield "", line
            continue
        marker, info = match.groups()
        closing = re.compile(r"^ {0,3}" + marker[0] + "{" + str(len(marker)) + r",}\s*$")
        fenced = [line]
        for content in lines:
            fenced.append(content)
            if closing.fullmatch(content):
                yield info.strip().casefold() or "code", "\n".join(fenced)
                break


def er_views(text):
    for language, block in blocks(text):
        if language != "mermaid":
            continue
        content = "\n".join(block.splitlines()[1:-1]).strip()
        # Mermaid permits YAML front matter and %% comments before the diagram declaration.
        content = re.sub(r"\A---\s*\n.*?\n---[ \t]*\n", "", content, count=1, flags=re.S)
        first = next((s.strip() for s in content.splitlines() if s.strip() and not s.lstrip().startswith("%%")), "")
        if first.split(maxsplit=1)[:1] == ["erDiagram"]:
            yield block


def cell_text(cell):
    value = re.sub(r"""<a\s+id=["'][^"']+["']\s*></a>""", "", cell)
    value = re.sub(r"\[([^\[\]]+)\]\([^()]+\)", r"\1", value)
    value = re.sub(r"`([^`]+)`", r"\1", value)
    return value.strip().removeprefix("**").removesuffix("**").replace(r"\|", "|")


def cells(line):
    return [cell_text(cell) for cell in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def mermaid_text(value):
    # Mermaid decodes its numeric entities after tokenization. Escape the unanchored
    # "direction LR" lexer rule too: even text inside a quoted state can match it.
    value = re.sub(r'["<>:;#%&{}`\[\]\\|]', lambda m: f"#{ord(m[0])};", value)
    return re.sub(r"d(?=irection\s+(?:LR|RL|BT|TB))", lambda m: f"#{ord(m[0])};", value, flags=re.I)


MARKER = re.compile(r"\s*\((initial|final|начальн\w*|конечн\w*|терминальн\w*)\)\s*$", re.I)
MISSING = {"", "—", "–", "-"}
STAY = MISSING | {"stay", "остается", "остаётся", "без изменений"}


def state_name(cell):
    marker = MARKER.search(cell)
    if not marker:
        return cell, ""
    return cell[:marker.start()].strip(), (
        "initial" if marker[1].casefold().startswith(("initial", "начальн")) else "final"
    )


def state_diagram(table):
    headers = [name.casefold() for name in cells(table[0])]
    columns = {key: i for i, header in enumerate(headers) for key, pattern in COLUMN.items()
               if re.fullmatch(pattern, header)}
    if not {"state", "target", "event"} <= columns.keys() or len(table) < 3:
        return ""
    if not all(re.fullmatch(r":?-+:?", sep) for sep in cells(table[1])):
        return ""
    states, starts, finals, edges = {}, [], [], []
    for line in table[2:]:
        data = cells(line)
        if len(data) != len(headers):
            return ""   # A malformed table cannot support a faithful diagram.
        row = {key: data[pos] for key, pos in columns.items()}
        source, source_marker = state_name(row["state"])
        target, target_marker = state_name(row["target"])
        if not source or not target and target_marker:
            return ""
        same = target.casefold() in STAY
        if same:
            target = source
        for state, marker in ((source, source_marker), (target, target_marker)):
            states.setdefault(state, f"St{len(states) + 1}")
            if marker == "initial" and state not in starts:
                starts.append(state)
            if marker == "final" and state not in finals:
                finals.append(state)
        event, guard, effect = (row.get(key, "") for key in ("event", "guard", "effect"))
        if same and event in MISSING and guard in MISSING and row["target"].casefold() in MISSING:
            continue   # A terminal declaration can describe cleanup without declaring another transition.
        label = []
        if event not in MISSING:
            label.append(mermaid_text(event))
        if guard not in MISSING:
            label.append("[" + mermaid_text(guard) + "]")
        if effect not in MISSING:
            label.append("/ " + mermaid_text(effect))
        edges.append(f"    {states[source]} --> {states[target]}" + (" : " + "<br/>".join(label) if label else ""))
    lines = ["```mermaid", "stateDiagram-v2"]
    lines.extend(f'    state "{mermaid_text(name)}" as {alias}' for name, alias in states.items())
    lines.extend(f"    [*] --> {states[name]}" for name in starts or [next(iter(states))])
    lines.extend(edges)
    lines.extend(f"    {states[name]} --> [*]" for name in finals)
    return "\n".join([*lines, "```"])


def state_views(text):
    # Keep the mechanism across subheadings, stopping at the next sibling or parent.
    mechanism, depth = "", 0
    lines = ("" if language else value for language, value in blocks(text))
    for is_table, group in groupby(lines, key=lambda line: line.lstrip().startswith("|")):
        if is_table:
            if mechanism and (diagram := state_diagram(list(group))):
                yield f"### {mechanism} state transitions\n\n{diagram}"
            continue
        for line in group:
            if match := HEADING.match(line):
                level, heading = len(match[1]), match[2]
                if level <= depth:
                    mechanism = ""
                owners = re.findall(r"\bMC-\d+\b", heading)
                if len(owners) == 1:
                    mechanism, depth = owners[0], level


def render_detail_diagrams(project_dir: Path) -> str:
    sections = []
    data = project_dir / "data.md"
    if data.is_file():
        diagrams = list(er_views(data.read_text(encoding="utf-8")))
        if diagrams:
            sections.append("### Entity relationships\n\n" + "\n\n".join(diagrams))
    mechanics = project_dir / "mechanics.md"
    if mechanics.is_file():
        sections.extend(state_views(mechanics.read_text(encoding="utf-8")))
    return "\n\n".join(sections)
