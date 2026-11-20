"""Stable links point at the owning record in repository Markdown."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

LINK = Path(__file__).resolve().parents[1] / "skills/requirements/scripts/link_docs.py"


class DesignAnchorTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.directory = Path(tmp.name)

    def link(self, *options):
        return subprocess.run([sys.executable, "-B", str(LINK), self.directory, *options],
                              text=True, capture_output=True)

    def test_all_destinations_are_unique_and_idempotent(self):
        documents = {
            "high-level-design.md": """# Архитектура
| ID | Used by | Link |
|---|---|---|
| I-1 | operator | B-1 |

| ИД | Часть | Ответственность |
|---|---|---|
| B-1 | Датчик | Измерение |
| B-2 | Приёмник | Приём |

| ID | Откуда → куда | Что передаётся и зачем |
|---|---|---|
| I-1 | B-1 → B-2 | Измерение |

| ID | Scenario | Steps |
|---|---|---|
| S-1 | Main | B-1 → I-1 → B-2 |
""",
            "data.md": """# Data
## Traceability
| ID | Entity | Used by |
|---|---|---|
| E-1 | Cross-reference | instrument |

## Logical fields
| Entity | Field | Meaning |
|---|---|---|
| E-1 | identity | names the sensor |

## Lifecycle and copies
| ID | Created by | Deleted by |
|---|---|---|
| E-1 | sensor | operator |

## Entity catalog
| ID | Entity | Meaning |
|---|---|---|
| E-1 | Sample | Temperature |

<a id="E-1-reading"></a>
**Entity:** E-1 · **Aspect:** reading · **Representation:** derived

| ID | Region | Contents |
|---|---|---|
| M-1 | Ring | Samples |
""",
            "mechanics.md": """# Mechanics
## Mechanisms
| ID | Part | Mechanism |
|---|---|---|
| MC-1 | B-2 | Accept |
| MC-2 | B-2 | Queue |

### MC-1 Sample acceptance
Guard and effects.

#### MC-1 Sample acceptance, continued
Additional context.
""",
            "contracts.md": """# Contracts
| ID | Boundary | Direction |
|---|---|---|
| X-1 | Port | external |
| I-1 | Sensor | internal |
""",
            "resource-math.md": """# Math
<!-- model:begin -->
| ID | Metric | Limit |
|---|---|---|
| L-1 | rate | 50 |
<!-- model:end -->

| ID | Assumption | Expected |
|---|---|---|
| A-1 | Arrival rate | 40 |

| ID | Limit | Verdict |
|---|---|---|
| L-1 | Service rate | fits |
""",
        }
        for name, content in documents.items():
            (self.directory / name).write_text(content)
        expected = {"B-1": "Датчик", "B-2": "Приёмник", "I-1": "Измерение", "S-1": "Main",
                    "E-1": "Sample", "M-1": "Ring", "MC-2": "Queue", "X-1": "Port",
                    "A-1": "Arrival rate", "L-1": "Service rate"}
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        linked = {name: (self.directory / name).read_text() for name in documents}
        content = "\n".join(linked.values())
        for rid, name in expected.items():
            anchor = f'<a id="{rid}"></a>'
            self.assertEqual(content.count(anchor), 1, rid)
            self.assertRegex(content, re.escape(anchor) + r"\s*" + re.escape(name))
        self.assertEqual(content.count('<a id="MC-1"></a>'), 1)
        self.assertIn('<a id="MC-1"></a>\n### MC-1 Sample acceptance', content)
        self.assertIn('<a id="E-1-reading"></a>\n**Entity:**', content)
        self.assertEqual(self.link().returncode, 0)
        self.assertEqual(linked, {name: (self.directory / name).read_text() for name in documents})

    def test_examples_and_secondary_tables_cannot_define_entities(self):
        path = self.directory / "data.md"
        path.write_text("""# Data
   ~~~~markdown
| ID | Entity |
|---|---|
| E-7 | Fenced example |
~~~
| E-6 | Still fenced |
~~~~

| Entity | Field | Meaning |
|---|---|---|
| E-1 | field | Orphaned |

| ID | Created by | Changed by |
|---|---|---|
| E-2 | creator | changer |

| ID | Entity |
|---|---|
| E-3 |   |
| E-4 | bad | width |
| E-5 | OK |

<!-- unpublished example
| ID | Entity |
|---|---|
| E-8 | Hidden |
-->
""")
        result = self.link()
        content = path.read_text()
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        for rid in ("E-1", "E-2", "E-3", "E-4"):
            self.assertRegex(result.stdout, rid + r".*not defined in data.md")
            self.assertNotIn(f'<a id="{rid}"></a>', content)
        self.assertNotIn("E-6", result.stdout)
        self.assertNotIn("E-7", result.stdout)
        self.assertNotIn("E-8", result.stdout)
        self.assertEqual(re.findall(r'<a id="(.*?)"></a>', content), ["E-5"])

    def test_new_detail_replaces_the_catalog_anchor(self):
        path = self.directory / "mechanics.md"
        path.write_text("# Mechanics\n## Mechanisms\n| ID | Mechanism |\n|---|---|\n| MC-1 | Accept |\n")
        self.assertEqual(self.link().returncode, 0)
        self.assertIn('<a id="MC-1"></a>Accept', path.read_text())
        with path.open("a") as document:
            document.write('\n### MC-1 Accept\nGuard and effect.\n\n## Traceability\n## MC-1 Coverage\n')
        self.assertEqual(self.link().returncode, 0)
        linked = path.read_text()
        self.assertEqual(linked.count('<a id="MC-1"></a>'), 1)
        self.assertIn('<a id="MC-1"></a>\n### MC-1 Accept', linked)
        self.assertEqual(self.link().returncode, 0)
        self.assertEqual(path.read_text(), linked)

    def test_localized_generic_names_in_legacy_catalogs(self):
        (self.directory / "data.md").write_text("""# Data
## 1. Каталог сущностей
| ID | Имя |
|---|---|
| E-1 | Registration |

## Logical fields
| ID | Name | Meaning |
|---|---|---|
| E-1 | Key | Unique |

## 3. Memory strategy
| ID | Name |
|---|---|
| M-1 | Buffer |
""")
        (self.directory / "contracts.md").write_text("""# Contracts
| ID | Наименование | Direction | Spec |
|---|---|---|---|
| X-1 | Device | published | device.yaml |
""")
        (self.directory / "architecture.md").write_text("""# Architecture
## Части
| ID | Название |
|---|---|
| B-1 | Instrument |
""")
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        content = "\n".join(path.read_text() for path in self.directory.glob("*.md"))
        for rid, name in (("E-1", "Registration"), ("M-1", "Buffer"), ("X-1", "Device"), ("B-1", "Instrument")):
            self.assertIn(f'<a id="{rid}"></a>{name}', content)
            self.assertEqual(content.count(f'<a id="{rid}"></a>'), 1)

    def test_heading_only_records_link_to_the_first_owning_heading(self):
        path = self.directory / "high-level-design.md"
        (self.directory / "data.md").write_text("# Data\n### E-1: Sample\n")
        path.write_text("""# Architecture
### S-1. Main path
Walk through the response.

## Traceability
### S-1 Additional references
### E-1 Foreign entity
""")
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        linked = path.read_text()
        self.assertIn('<a id="S-1"></a>\n### S-1. Main path', linked)
        self.assertEqual(linked.count('<a id="S-1"></a>'), 1)
        self.assertNotIn('<a id="E-1"></a>', linked)
        self.assertEqual(self.link().returncode, 0)
        self.assertEqual(linked, path.read_text())

    def test_anchors_only_preserves_other_project_files_and_line_endings(self):
        files = {
            "appendix/query.md": b"[Query index](index.md)\n",
            "appendix/index.md": b"# Query index\n",
            "decisions.md": b"# Decisions\n\n### D-1: Keep raw text\n",
            "research/R-1-case.md": b"# R-1 Case\n",
            "requirements.md": b"# Requirements\nD-1 and [R-1]\n",
        }
        for name, content in files.items():
            path = self.directory / name
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(content)
        architecture = self.directory / "architecture.md"
        source = (b"# Design\r\n\r\n### S-1. Main\r\nD-1 and [R-1]\r\n"
                  b'| Example | `<a id="S-1"></a>` |\r\n')
        architecture.write_bytes(source)
        for _ in range(2):
            result = self.link("--anchors-only")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(architecture.read_bytes(), source.replace(b"###", b'<a id="S-1"></a>\r\n###'))
            self.assertEqual({name: (self.directory / name).read_bytes() for name in files}, files)

    def test_full_linker_preserves_user_indexes_and_unknown_broken_links(self):
        appendix = self.directory / "appendix"
        appendix.mkdir()
        (appendix / "index.md").write_text("# Query index\n")
        (self.directory / "decisions.md").write_text("# Decisions\n")
        (self.directory / "concept.md").write_text("# Concept\n")
        query = appendix / "query.md"
        body = """[Query index](index.md) · [project](../index.md) · [external](https://example.org/index.md)
[Unpublished](future/decisions-notes/index.md)
[Unrelated](notes-on-concept.md) · [Another concept](other-project/concept.md)
[Previous layout](../01-concept.md)
"""
        query.write_text(body)
        result = self.link()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("[Query index](index.md)", query.read_text())
        self.assertIn("[external](https://example.org/index.md)", query.read_text())
        self.assertIn("[Unpublished](future/decisions-notes/index.md)", query.read_text())
        self.assertIn("[Unrelated](notes-on-concept.md)", query.read_text())
        self.assertIn("[Another concept](other-project/concept.md)", query.read_text())
        self.assertIn("[Previous layout](../concept.md)", query.read_text())
        self.assertNotIn("[project]", query.read_text())
