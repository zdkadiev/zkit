"""Markdown design navigation reads declarations and keeps their published links portable."""
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "flow" / "scripts"
sys.path.insert(0, str(SCRIPTS))
from design_inventory import access_by_part, load_project, render_inventory


class InventoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "my instrument"
        self.project.mkdir()

    def put(self, name, text):
        path = self.project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def test_navigation_regenerates_from_authoritative_records(self):
        self.put("architecture.md", """# Instrument
| ID | Part | Parent | Owns (E-n, in-process state) | Faces (X-n) |
|---|---|---|---|---|
| B-1 | Sampler | — | — | — |
| B-2 | Controller <a id="B-2"></a> | — | E-1, E-2, M-1 | X-1 |
| B-3 | Display | B-2 | — | — |

| ID | From → to | What passes and why | Protocol | Entity effects | Resources |
|---|---|---|---|---|---|
| I-1 | B-1 (publisher) → B-2, B-3 | Send frame | UART | B-2 reads E-1 and updates E-2 under MC-1. B-3 reads M-1. | M-1, L-1 |
| I-2 | B-1 → B-2 | Reset | UART | none | — |

| ID | Scenario | Steps (B-/I- ids) | Alternate path | Outcome against requirements |
|---|---|---|---|---|
| S-1 | Delayed frame | B-1 → I-1 → B-2 | B-1 → I-2 → B-2 | Apply MC-1 |
""")
        self.put("data.md", """# Data
| ID | Entity | Meaning | Writers (actors) |
|---|---|---|---|
| E-1 | Registration | Active sensor | Operator |
| E-2 | Reading | Accepted frame | Controller |
| E-3 | Calibration | Independent fact | Engineer |

| Entity | Field | Meaning |
|---|---|---|
| E-1 | sensor ID | A physical sensor |

| ID | Region | Contents |
|---|---|---|
| M-1 | Ring | Frames |
""")
        self.put("contracts.md", """# Boundaries
| ID | Boundary | Protocol | Spec | Counterparty | Direction |
|---|---|---|---|---|---|
| X-1 | Serial console | UART | [console](contracts/console.yaml) | Console | published |
""")
        self.put("mechanics.md", """# Mechanisms
| ID | Part | Mechanism |
|---|---|---|
| MC-1 | B-2 | Sample acceptance |

| Interface | Spec | What the format must guarantee |
|---|---|---|
| I-1, I-2 | contracts/frame.yaml | Preserves registration identity |
""")
        self.put("resource-math.md", """# Math
| ID | Assumption | Expected |
|---|---|---|
| A-1 | Bus rate <a id="A-1"></a> | 800 |

| ID | Metric | Limit |
|---|---|---|
| L-1 | Throughput | 1000 |

### Capacity by resource

| Resource | Interfaces | Scenario | Window | Offered load | Sustainable throughput | Unit | Utilization | Sources | Calculation |
|---|---|---|---|---|---|---|---|---|---|
| Receiver M-1 | I-1, I-2 | normal | 1 s | 800 (estimated) | 1000 (measured) | frames/s | 80% | A-1, L-1 | [calc](resource-math/model.py) |
""")
        for path in ("contracts/frame.yaml", "contracts/console.yaml", "resource-math/model.py"):
            self.put(path, "")

        project = load_project(self.project)
        self.assertEqual([r.id for r in project.of_kind("I")], ["I-1", "I-2"])
        self.assertEqual(project.records["B-2"].name, "Controller")
        self.assertEqual(project.records["B-3"].parent, "B-2")
        self.assertEqual(project.records["B-2"].owns, ("E-1", "E-2", "M-1"))
        self.assertEqual(project.records["I-1"].participants, ("B-1", "B-2", "B-3"))
        self.assertEqual(project.records["I-1"].contract, "contracts/frame.yaml")
        self.assertEqual(project.records["I-2"].contract, "contracts/frame.yaml")
        self.assertEqual(project.records["X-1"].contract, "contracts/console.yaml")
        self.assertEqual(project.records["S-1"].alternate, "B-1 → I-2 → B-2")
        self.assertEqual(project.records["E-1"].name, "Registration")
        out = self.project.parent / "export" / "reader.md"
        out.parent.mkdir()
        self.assertEqual(project.source_url("B-2", out), "../my%20instrument/architecture.md#B-2")
        markdown = render_inventory(project, out)
        out.write_text(markdown, encoding="utf-8")
        for rid in ("E-1", "E-2", "E-3", "M-1", "I-1", "I-2", "X-1", "B-1", "B-2", "B-3", "S-1"):
            self.assertEqual(markdown.count(f'<a id="{rid}"></a>'), 1)
        reading = markdown.split('<a id="E-2"></a>')[1].split('<a id=')[0]
        self.assertIn("Writers", reading)
        self.assertIn("[B-2](#B-2)", reading)
        scope = markdown.split('<a id="B-2"></a>')[1].split('<a id=')[0]
        for rid in ("E-1", "M-1", "I-1", "I-2", "X-1", "B-3"):
            self.assertIn(f"](#{rid})", scope)
        self.assertIn("sequenceDiagram", markdown)
        self.assertIn("else Alternate path", markdown)
        self.assertIn("B1->>B2: I-2", markdown)
        self.assertEqual(markdown.count("800 (estimated)"), 1)
        self.assertIn("#A-1)", markdown)
        self.assertIn("#S-1)", markdown)
        self.assertIn("contracts/frame.yaml)", markdown)
        self.assertIn("resource-math/model.py)", markdown)
        self.assertTrue(all((out.parent / unquote(urlsplit(link).path)).is_file()
                            for link in re.findall(r'\]\(([^)]+)\)', markdown) if urlsplit(link).path))

        arch = self.project / "architecture.md"
        arch.write_text(arch.read_text().replace("UART", "SPI").replace("Controller", "Receiver"))
        updated = render_inventory(load_project(self.project), out)
        self.assertIn("SPI", updated)
        self.assertIn("Receiver", updated)
        self.assertIn('<a id="B-2"></a>', updated)

    def test_russian_and_legacy_tables_ignore_code_and_secondary_records(self):
        self.put("high-level-design.md", """# Архитектура
| ИД | Часть | Владеет | Границы |
|---|---|---|---|
| B-1 | Датчик | M-1 | X-1 |
| B-2 | Приёмник | E-1 | — |

| ID | Откуда → куда | Что передаётся и зачем | Стиль | Семантика доставки |
|---|---|---|---|---|
| I-1 | B-1 → B-2 | Кадр | событие | возможны потери |

### S-1. Приём кадра
""")
        self.put("data.md", """# Данные
| ID | Сущность | Кто пишет |
|---|---|---|
| E-1 | Отсчёт | Оператор |

| ID | Кем создан | Кем изменён |
|---|---|---|
| E-1 | Датчик | Приёмник |

| ID | Область | Содержимое |
|---|---|---|
| M-1 | Буфер | Кадры |

~~~markdown
| ID | Сущность |
|---|---|
| E-9 | Вымышленная |
~~~
""")
        self.put("contracts.md", """# Границы
| ID | Граница | Направление | Парадигма | Спецификация |
|---|---|---|---|---|
| X-1 | Порт | отдаёт | сигналы | — |
""")
        project = load_project(self.project)
        self.assertNotIn("E-9", project.records)
        self.assertEqual(project.records["E-1"].name, "Отсчёт")
        self.assertEqual(project.records["I-1"].document, "high-level-design.md")
        self.assertEqual(project.records["I-1"].protocol, "")
        self.assertEqual(project.records["I-1"].name, "Кадр")
        self.assertEqual(project.records["S-1"].name, "Приём кадра")
        self.assertEqual(project.records["B-1"].faces, ("X-1",))
        self.assertEqual(project.records["B-2"].owns, ("E-1",))
        command = [sys.executable, SCRIPTS / "design_inventory.py", self.project]
        subprocess.run(command, check=True, capture_output=True)
        expected = self.project / "diagrams" / "DESIGN.md"
        result = expected.read_text()
        self.assertIn("Protocol unspecified", result)
        self.assertIn("Оператор", result)
        self.assertNotIn("Вымышленная", result)
        self.assertIn("../high-level-design.md", result)
        subprocess.run(command, check=True, capture_output=True)
        self.assertEqual(result, expected.read_text())


    def test_explicit_mermaid_subgraph_and_output_collisions(self):
        self.put("architecture.md", """| ID | Part |
|---|---|
| B-1 | Parent |
| B-2 | Child |
| B-3 | Neighbor |

### Level 3 — Components of B-1

```mermaid
flowchart LR
    subgraph B1["Parent"]
        B2["Child"]
    end
    B2 --> B3
```
""")
        project = load_project(self.project)
        self.assertEqual(project.records["B-2"].parent, "B-1")
        self.assertFalse(project.records["B-3"].parent)
        view = render_inventory(project, self.project / "diagrams" / "DESIGN.md")
        self.assertIn('subgraph B1["Parent"]', view.split('<a id="B-1"></a>')[1].split('<a id=')[0])
        inventory = self.project / "diagrams" / "DESIGN.md"
        for path in (inventory, self.project / "notes.md"):
            path.parent.mkdir(exist_ok=True)
            path.write_text("Hand-written design")
            args = [] if path == inventory else ["--output", path]
            result = subprocess.run([sys.executable, SCRIPTS / "design_inventory.py", self.project, *args],
                                    text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(path.read_text(), "Hand-written design")

    def test_access_is_attributed_only_to_explicit_positive_objects(self):
        self.assertEqual(list(access_by_part("B-2 updates E-2 if E-1 is registered.")),
                         [("E-2", "write", "B-2")])
        self.assertEqual(list(access_by_part("B-2 reads E-1 but never writes E-2.")),
                         [("E-1", "read", "B-2")])
        self.assertEqual(list(access_by_part("B-2 reads E-1 and creates or updates E-2 under MC-1")),
                         [("E-1", "read", "B-2"), ("E-2", "write", "B-2")])
        self.assertEqual(list(access_by_part("B-1 and B-2 read E-1 and E-2.")),
                         [("E-1", "read", "B-1"), ("E-1", "read", "B-2"),
                          ("E-2", "read", "B-1"), ("E-2", "read", "B-2")])
