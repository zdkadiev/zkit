#!/usr/bin/env python3
"""Keep the documents of one zkit project linked. Idempotent; stdlib only.

Layout:
  docs/zkit/<project>/               a project: 'mvp', a big feature, ... (kebab-case name)
      concept.md
      requirements.md                (later stages: resource-math.md, ux.md (optional), contracts.md, data.md, architecture.md, ...: add to STAGES)
      decisions.md                   ONE file: entries '### D-<n>: title', each with an <a id="D-<n>"> anchor
      research/R-<n>-<slug>.md       one file per research question; ids unique inside the project

Usage:
  link_docs.py <project-dir>          turn mentions of D-n, [R-n] and 'concept §n' into links; rebuild the
                                      back-links under each decision, 'Используется в' in research reports and
                                      the summary table at the top of decisions.md; anchor design records and verify every cited id
                                      against the registry IDS below (exit 1 on errors)
  link_docs.py <project-dir> --anchors-only
                                      publish stable design record anchors for browsing without rebuilding project links
  link_docs.py <zkit-root> --migrate --project <name>
                                      move an older layout (flat files, numbered files or folders, one file per
                                      decision) into <zkit-root>/<name>/ and repair the links
"""
import ast
import os, re, sys, glob, shutil
from pathlib import Path
from urllib.parse import unquote
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "flow", "scripts"))
try: from ids import IDS, rx   # the id registry: one owner document per prefix
except ImportError: sys.exit("ERROR: zkit id registry flow/scripts/ids.py not found: run this script from the zkit plugin, not from a copied skill")

from record_anchors import NAME_COLUMNS, add_record_anchors, content_lines, heading_records, record_rows

STAGES = ["concept", "requirements", "resource-math", "ux", "contracts", "data", "architecture", "mechanics", "resilience", "roadmap"]   # later stages: add here and to stage_docs below
ROW_IDS = rx(*[k for k in IDS if k not in {"D", "R", "P", "Q"}])   # ids defined as table rows
rd = lambda p: open(p, encoding="utf-8").read()
def wr(p, s):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True); open(p, "w", encoding="utf-8").write(s)
def rel(frm, to): return os.path.relpath(to, os.path.dirname(frm)).replace(os.sep, "/")
ENTRY = re.compile(r'(?:<a id="' + rx("D") + r'"></a>\n)?^###\s*D-(\d+)\s*(?:\(([^)]*)\))?\s*:\s*(.+?)\n(.*?)(?=^(?:<a id="' + rx("D") + r'"></a>\n)?###\s*D-|\Z)', re.M | re.S)
def entry_text(n, title, status, date, body):
    return '<a id="D-%s"></a>\n### D-%s: %s\n> **Статус:** %s · **Дата:** %s\n\n%s\n' % (n, n, title.strip(), status, date, body.strip())

arg = next((a for a in sys.argv[1:] if not a.startswith("--")), "docs/zkit")
anchors_only = "--anchors-only" in sys.argv
if anchors_only and any(option in sys.argv for option in ("--migrate", "--fix-ids", "--project")):
    sys.exit("ERROR: --anchors-only takes only the project directory")
if anchors_only and not os.path.isdir(arg):
    sys.exit("ERROR: project directory does not exist: " + arg)

# ---------- migration of older layouts into <root>/<project>/
if "--migrate" in sys.argv:
    root = arg
    name = sys.argv[sys.argv.index("--project") + 1] if "--project" in sys.argv else "mvp"
    d = os.path.join(root, name); os.makedirs(d, exist_ok=True)
    def grab(dest, *patterns):
        for pat in patterns:
            hit = sorted(glob.glob(os.path.join(root, pat)))
            if hit:
                shutil.move(hit[0], os.path.join(d, dest)); return True
    grab("concept.md", "concept/[0-9][0-9]-*.md", "01-concept/concept.md", "01-concept.md")
    grab("requirements.md", "requirements/[0-9][0-9]-*.md", "02-requirements/requirements.md", "02-requirements.md")
    if os.path.isdir(os.path.join(root, "research")): shutil.move(os.path.join(root, "research"), os.path.join(d, "research"))
    entries = {}
    srcs = sorted(glob.glob(os.path.join(root, "decisions", "[0-9][0-9]-*.md")))
    if srcs:
        for m in ENTRY.finditer(rd(srcs[0])): entries[int(m.group(1))] = m.group(0).strip() + "\n"
        shutil.rmtree(os.path.join(root, "decisions"))
    elif os.path.exists(os.path.join(root, "decisions.md")):       # flat journal
        for m in ENTRY.finditer(rd(os.path.join(root, "decisions.md"))):
            n, note, title, body = m.groups(); body = body.strip()
            date = (re.search(r"Дата:\s*([\d-]+)", body) or [None, "—"])[1]
            status = "принято"
            if note:
                nm = re.search(r"D-(\d+)", note)
                verb = "заменено" if re.search(r"заменено|superseded", note, re.I) else "уточнено"
                status = "%s [D-%s](#D-%s)" % (verb, nm.group(1), nm.group(1)) if nm else note
            entries[int(n)] = entry_text(n, title, status, date, body)
        os.rename(os.path.join(root, "decisions.md"), os.path.join(root, "decisions.md.migrated"))
    elif glob.glob(os.path.join(root, "decisions", "D-*.md")):     # one file per decision
        for f in glob.glob(os.path.join(root, "decisions", "D-*.md")):
            t = rd(f).split("\n## Связи")[0]
            m = re.match(r"#\s*D-(\d+):\s*(.*?)\n+> \*\*Статус:\*\*\s*(.*?)\s*·\s*\*\*Дата:\*\*\s*([\d—-]+)\n+(.*)", t, re.S)
            if m:
                n, title, status, date, body = m.groups()
                entries[int(n)] = entry_text(n, title, re.sub(r"\[(" + rx("D") + r")\]\(D-(\d+)\.md\)", r"[\1](#D-\2)", status), date, body)
        shutil.rmtree(os.path.join(root, "decisions"))
    if entries:
        wr(os.path.join(d, "decisions.md"), "# Решения: %s\n\n" % name + "\n".join(entries[k] for k in sorted(entries)))
    for ix in (os.path.join(root, "index.md"), os.path.join(root, "decisions", "index.md")):   # indexes are gone
        if os.path.exists(ix): os.remove(ix)
    arg = d
    print("migrated into", d)

d = arg
P = lambda *a: os.path.join(d, *a)
concept_p, req_p, dec_p = P("concept.md"), P("requirements.md"), P("decisions.md")
hld_p = P("architecture.md") if os.path.exists(P("architecture.md")) else P("high-level-design.md")
rm_p = P("resource-math.md")
mc_p = P("mechanics.md")
rs_p = P("resilience.md")
rmp_p = P("roadmap.md")
ct_p = P("contracts.md")
dt_p = P("data.md")
if_p = P("ux.md")
design_paths = [path for path in (hld_p, ct_p, dt_p, mc_p, rm_p) if os.path.isfile(path)]

def publish_design_anchors():
    changed = 0
    for filename in design_paths:
        path = Path(filename)
        source = path.read_bytes().decode("utf-8")  # preserve every original line ending
        anchored = add_record_anchors(filename, source)
        if anchored != source:
            path.write_bytes(anchored.encode("utf-8"))
            changed += 1
    return changed

if anchors_only:
    print("anchors: %d design document(s) updated" % publish_design_anchors())
    sys.exit(0)

rfiles = {re.match(rx("R"), os.path.basename(f)).group(0): f for f in glob.glob(P("research", "R-*.md"))}
stage_docs = [p for p in (concept_p, req_p, rm_p, if_p, ct_p, dt_p, hld_p, mc_p, rs_p, rmp_p) if os.path.exists(p)]

# ---------- repair links that no longer resolve (after a migration or a rename)
legacy_roots = [Path(d).resolve()]
if "--migrate" in sys.argv:
    legacy_roots.append(Path(root).resolve())
retired_indexes = {base / name for base in legacy_roots for name in ("index.md", "decisions/index.md")}
def repair(f):
    t = rd(f)
    def fix(m):
        tgt, frag = m.group(2), m.group(3) or ""
        if re.match(r"^(?:[a-z][\w+.-]*:|//)", tgt, re.I):
            return m.group(0)
        target = (Path(f).parent / unquote(tgt)).resolve()
        if target.exists():
            return m.group(0)
        if target in retired_indexes:
            return ""
        if target.name == "index.md":
            return m.group(0)
        # Only names and locations used by a previous zkit layout can be redirected.
        b = target.name
        dm = re.fullmatch(r"D-(\d+)\.md", b)
        new = None
        if dm and (target.parent in {base / "decisions" for base in legacy_roots} or
                   (f == dec_p and target.parent in legacy_roots)):
            new = dec_p, "#D-" + dm[1]
        for key, names, path in (
            ("concept", ("concept.md", "01-concept.md"), concept_p),
            ("requirements", ("requirements.md", "02-requirements.md"), req_p),
            ("decisions", ("decisions.md",), dec_p),
        ):
            stage_folder = target.parent.parent in legacy_roots and re.fullmatch(r"(?:\d{2}-)?" + key, target.parent.name)
            if (target.parent in legacy_roots and b in names) or (stage_folder and (b in names or re.fullmatch(r"\d{2}-.+\.md", b))):
                new = path, frag
        rm = re.fullmatch(r"(" + rx("R") + r")(?:-[^/]*)?\.md", b)
        if new is None and rm and rm[1] in rfiles and target.parent in {base / "research" for base in legacy_roots}:
            new = rfiles[rm[1]], frag
        if new is None or not os.path.exists(new[0]): return m.group(0)
        return "%s(%s%s)" % (m.group(1), rel(f, new[0]), new[1])
    lines = t.splitlines(keepends=True)
    for index, line in content_lines(lines):
        # Work backwards so dropping a retired link can consume one adjacent separator.
        for match in reversed(list(re.finditer(r"(\[[^\]]*\])\(([^)#\s]+\.md)(#[^)\s]*)?\)", line))):
            replacement = fix(match)
            if replacement == match[0]:
                continue
            start, end = match.span()
            if not replacement:
                before = re.search(r"[ \t]*·[ \t]*$", line[:start])
                after = re.match(r"[ \t]*·[ \t]*", line[end:])
                if before:
                    start = before.start()
                elif after:
                    end += after.end()
            line = line[:start] + replacement + line[end:]
        lines[index] = line
    u = "".join(lines)
    if u != t: wr(f, u)
for f in glob.glob(P("**", "*.md"), recursive=True):
    repair(f)

def d_ids(): return set("D-" + x for x in re.findall(r"^###\s*D-(\d+)", rd(dec_p), re.M)) if os.path.exists(dec_p) else set()

# ---------- 1. linkify mentions in concept and requirements
def linkify(path):
    out, fence, ids = [], False, d_ids()
    for line in rd(path).split("\n"):
        if line.startswith("```"): fence = not fence
        if fence or line.startswith("#") or line.startswith(">") or line.startswith("<a id"):
            out.append(line); continue
        line = re.sub(r"(?<![\w\[/(#-])(" + rx("D") + r")(?![\w\]-])(?!\]\()", lambda m: "[%s](%s#%s)" % (m.group(1), rel(path, dec_p), m.group(1)) if m.group(1) in ids else m.group(0), line)
        line = re.sub(r"\[(" + rx("R") + r")\](?!\()", lambda m: "[%s](%s)" % (m.group(1), rel(path, rfiles[m.group(1)])) if m.group(1) in rfiles else m.group(0), line)
        if path != concept_p and os.path.exists(concept_p):
            line = re.sub(r"(?<![\[\w])((?:concept|концепт)\s*§\s*\d+(?:[,\s]*§\s*\d+)*)(?!\]\()", lambda m: "[%s](%s)" % (m.group(1), rel(path, concept_p)), line, flags=re.I)
        out.append(line)
    open(path, "w", encoding="utf-8").write("\n".join(out))
for f in stage_docs: linkify(f)
# Publish links only for declared design constraints and leave code, URLs, existing
# links, table keys and generated resource-math blocks intact.
constraint_ids = {rid for _, rid, _ in record_rows(hld_p, rd(hld_p)) if rid.startswith("DC-")} if os.path.isfile(hld_p) else set()
contract_cards = [str(card) for card in Path(d, "contracts").rglob("*.md") if card.is_file() and not card.is_symlink()]
if constraint_ids:
    mention = re.compile(r"(?P<skip>`+[^`]*`+|!?\[[^\]]*\](?:\([^)]*\)|\[[^\]]*\])?|<[^>]*>|(?:https?://|\S*/)[^\s|]+)|(?<![\w/#-])(?P<id>DC-\d+)(?![\w-])")
    for filename in stage_docs + contract_cards:
        source = Path(filename).read_bytes().decode("utf-8")
        lines = source.splitlines(keepends=True)
        def constraint_link(match):
            rid = match["id"]
            if rid not in constraint_ids:
                return match[0]
            document = "" if filename == hld_p else rel(filename, hld_p)
            return f"[{rid}]({document}#{rid})"

        for index, line in content_lines(lines, skip_model=True):
            if re.match(r"^\s*(?:#|>|\[[^\]]+\]:)", line):
                continue
            # The first table cell declares a record or serves as its lookup key.
            start = line.find("|", line.find("|") + 1) + 1 if line.lstrip().startswith("|") else 0
            lines[index] = line[:start] + mention.sub(constraint_link, line[start:])
        result = "".join(lines)
        if result != source:
            Path(filename).write_bytes(result.encode("utf-8"))
publish_design_anchors()

# ---------- 2. mentions: key -> {doc: [labels]}
def labels(path):
    res, head = {}, ""
    for line in rd(path).split("\n"):
        h = re.match(r"#+\s*(.*)", line)
        if h: head = h.group(1).strip(); continue
        idm = re.match(r"\|\s*(%s)\s*\|" % ROW_IDS, line) or re.match(r"\s*(?:[-*]|\d+\.)\s*\*\*(" + rx("P", "Q") + r")\.", line)
        label = idm.group(1) if idm else re.sub(r"\s+", " ", head)[:60] or "—"
        for k in set(re.findall(r"\b(" + rx("D") + r")\b", line)) | set("R-" + x for x in re.findall(r"\bR-(\d+)\b", line)):
            res.setdefault(k, []).append(label)
    return res
mentions = {}
for f in stage_docs:
    for k, labs in labels(f).items(): mentions.setdefault(k, {}).setdefault(f, []).extend(labs)
def links_for(key, own):
    return ["[%s](%s): %s" % (os.path.basename(f), rel(own, f), ", ".join(dict.fromkeys(mentions[key][f]))) for f in stage_docs if f in mentions.get(key, {})]

# ---------- 3. decisions.md: back-links per entry and a summary table
if os.path.exists(dec_p):
    t = rd(dec_p); ents = list(ENTRY.finditer(t))
    head = re.split(r"\n## Сводка", t[:ents[0].start()] if ents else t)[0].rstrip("\n") + "\n"
    rows, body = [], []
    for m in ents:
        n, note, title, b = m.groups(); key = "D-" + n
        b = re.sub(r"\n?<!-- links -->.*?<!-- /links -->\n?", "\n", b, flags=re.S).rstrip("\n")
        st = (re.search(r"Статус:\*\*\s*(.*?)\s*·", b) or [None, note or "принято"])[1]
        rows.append("| [%s](#%s) | %s | %s |" % (key, key, title.strip(), st))
        refs = links_for(key, dec_p)
        for o in ents:
            ob = re.sub(r"<!-- links -->.*?<!-- /links -->", "", o.group(4), flags=re.S)
            if o is not m and re.search(r"\b%s\b" % key, ob): refs.append("[D-%s](#D-%s): упоминает" % (o.group(1), o.group(1)))
        body.append(('<a id="D-%s"></a>\n### D-%s: %s\n' % (n, n, title.strip())) + b + "\n\n<!-- links -->\n**Связи:** " + ("; ".join(refs) if refs else "пока нигде не используется") + "\n<!-- /links -->\n")
    wr(dec_p, head + "\n## Сводка\n\n| # | Решение | Статус |\n|---|---|---|\n" + "\n".join(rows) + "\n\n## Решения\n\n" + "\n".join(body))

# ---------- 4. research reports: used in
for key, f in rfiles.items():
    body = re.split(r"\n## (?:Используется в|Used in)", rd(f))[0].rstrip("\n")
    refs = links_for(key, f)
    wr(f, body + "\n\n## Используется в\n<!-- собирается link_docs.py, не править вручную -->\n" + ("\n".join("- " + r for r in refs) or "- пока нигде не используется") + "\n")
print("linked: %s — %d stage documents, %d decisions, %d reports" % (os.path.basename(os.path.abspath(d)), len(stage_docs), len(d_ids()), len(rfiles)))

# ---------- 5. verify ids against the registry: cited ids must exist in their owner, validations must be planned
owner_p = {"requirements.md": req_p, "resource-math.md": rm_p, "ux.md": if_p, "contracts.md": ct_p, "data.md": dt_p,
           "architecture.md": hld_p, "mechanics.md": mc_p, "resilience.md": rs_p, "roadmap.md": rmp_p}
def nofence(text): return "\n".join(line for _, line in content_lines(text.splitlines()))
docs_all = stage_docs + glob.glob(P("roadmap", "**", "*.md"), recursive=True) + list(rfiles.values()) + ([dec_p] if os.path.exists(dec_p) else [])
if "--fix-ids" in sys.argv and os.path.exists(req_p) and re.search(r"\*\*К-\d+", rd(req_p)) and not re.search(r"\*\*Q-\d+", rd(req_p)):
    for f in docs_all:   # the old requirements template numbered conflicts with Cyrillic К-n; the registry calls them Q-n
        t = rd(f); u = re.sub(r"(?<![\w-])К-(\d+)\b", r"Q-\1", t)
        if u != t: wr(f, u); print("fixed: К-n -> Q-n in", os.path.relpath(f, d))
texts = {f: nofence(rd(f)) for f in docs_all}
BULLET = r"^\s*(?:[-*]|\d+\.)\s*\*\*(%s)-(\d+)(?:\.| \()"
LOCAL = r"^(?:\s*(?:[-*]|\d+\.)\s*\*\*|#{1,6}\s*|\|\s*)(%s)-(\d+)\b"   # where a document defines an item: list label, heading, first table cell
design_ids = {}
for path in design_paths:
    source = rd(path)
    design_ids[path] = {rid for _, rid, _ in record_rows(path, source)}
    design_ids[path].update(rid for _, rid, _ in heading_records(path, source))

def owner_defs(pre, path):
    t = texts[path]
    if pre in ("P", "Q"): return set("%s-%s" % m for m in re.findall(BULLET % pre, t, re.M))
    if pre in NAME_COLUMNS:
        found = {rid for rid in design_ids[path] if rid.partition("-")[0] == pre}
    else:
        found = set(re.findall(r"^#{1,6}\s*(%s-\d+)\b" % pre, t, re.M))
        found.update(re.findall(r"^\|\s*(%s-\d+)\s*\|" % pre, t, re.M))
    if pre == "DC": return found  # Architecture owns these rows. A model can only consume them.
    stem = os.path.splitext(os.path.basename(path))[0]   # models: resource-math/model.py, resilience/model.py, or a legacy *model*.py in the root
    for py in glob.glob(P(stem, "**", "*.py"), recursive=True) + glob.glob(P("*model*.py")):
        found |= set(re.findall(r"""["'](%s-\d+)["']\s*:""" % pre, rd(py)))
    return found
defined = {"D": d_ids(), "R": set(rfiles)}
for pre, (own, _) in IDS.items():
    if own in owner_p and os.path.exists(owner_p[own]): defined[pre] = owner_defs(pre, owner_p[own])
validations = defined.get("P", set())
cited = {}
for f, t in texts.items():
    for pre, n in re.findall(r"(?<![\w-])(%s)-(\d+)\b" % "|".join(sorted(IDS, key=len, reverse=True)), t):
        cited.setdefault("%s-%s" % (pre, n), set()).add(os.path.relpath(f, d))
# A boundary spec or executable model can be the only consumer of a constraint.
# These files cite design IDs; definitions are exclusively in architecture.md.
for folder, suffixes in (("contracts", {".md", ".yaml", ".yml", ".json"}), ("mechanics", {".py"}), ("resource-math", {".py"})):
    for item in Path(d, folder).rglob("*"):
        if item.suffix.lower() not in suffixes or item.is_symlink() or not item.is_file():
            continue
        if item.suffix == ".py":
            # Bound lookups use literal string keys. Template comments and
            # explanatory prose are examples and must not create dependencies.
            try:
                tree = ast.parse(item.read_bytes(), filename=str(item))
            except (SyntaxError, ValueError):
                continue  # The owning stage diagnoses an invalid model.
            references = {node.value for node in ast.walk(tree) if isinstance(node, ast.Constant)
                          and isinstance(node.value, str) and re.fullmatch(r"DC-\d+", node.value)}
        else:
            source = item.read_text(encoding="utf-8")
            if item.suffix.lower() == ".md":
                source = nofence(source)
            elif item.suffix.lower() in {".yaml", ".yml"}:
                source = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("#"))
            references = set(re.findall(r"(?<![\w-])DC-\d+(?![\w-])", source))
        for rid in references:
            cited.setdefault(rid, set()).add(os.path.relpath(item, d))
# local numbering: a document other than the owner defines its own items with an id-like prefix -> one finding per document and prefix
local = {}
for f in stage_docs:
    for line in texts[f].splitlines():
        m = re.match(LOCAL % r"[A-ZА-ЯЁ]{1,3}", line)
        if not m: continue
        x, i = m.group(1), "%s-%s" % m.groups()
        if x in IDS and (owner_p.get(IDS[x][0]) == f or i in defined.get(x, ())): continue   # the owner itself, or a citation of a real id
        local.setdefault((f, x), []).append(i)
errs, warns = [], []
for (f, x), xs in sorted(local.items()):
    rf, xs = os.path.relpath(f, d), ", ".join(dict.fromkeys(xs))
    if x in IDS: errs.append("%s numbers its own items %s with the prefix of the registry's %s (owner %s): number them plainly (1., 2.) or cite the owner's ids" % (rf, xs, IDS[x][1], IDS[x][0]))
    elif re.search(r"(?m)^\s*(?:[-*]|\d+\.)\s*\*\*%s-\d" % x, texts[f]): errs.append("%s labels list items %s with a prefix that is not in the registry: number them plainly (1., 2.)%s" % (rf, xs, "; --fix-ids renames К-n to Q-n" if x == "К" and f == req_p else ""))
    else: warns.append("%s: prefix %s- (%s) is not in the id registry (flow/scripts/ids.py)" % (rf, x, xs))
flagged = {i for xs in local.values() for i in xs}
for i, fs in sorted(cited.items()):
    pre = i.split("-")[0]
    if i in flagged: continue
    if pre not in defined: warns.append("%s cited, but its owner %s does not exist yet" % (i, IDS[pre][0]))
    elif i not in defined[pre]: errs.append("%s (%s) is cited in %s but not defined in %s" % (i, IDS[pre][1], ", ".join(sorted(fs)), IDS[pre][0]))
if os.path.exists(rmp_p):
    plan = "\n".join(t for f, t in texts.items() if f == rmp_p or f.startswith(P("roadmap") + os.sep))
    warns += ["precondition %s is planned by no task or epic in roadmap (fine only if already done)" % v for v in sorted(validations) if not re.search(r"\b%s\b" % v, plan)]
for w in dict.fromkeys(warns): print("WARN", w)
for e in errs: print("ERROR", e)
print("ids: %d cited, %d errors" % (len(cited), len(errs)))
sys.exit(1 if errs else 0)
