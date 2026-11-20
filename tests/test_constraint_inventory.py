"""Follow a design constraint from the project inventory to the records it governs."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills/flow/scripts"
LINKER = ROOT / "skills/requirements/scripts/link_docs.py"
ARCHITECTURE = """# Instrument

| ID | Part | Responsibility |
|---|---|---|
| B-1 | Controller | Register devices |

## Design constraints

| ID | Parameter or rule | Allowed value | Scope | Basis | Applies to | Verification |
|---|---|---|---|---|---|---|
| DC-1 | Registrations | ≤ 16 registrations | Across both ports of B-1 | D-1, C-1 | B-1, X-1, E-1 | Run the [boundary check](mechanics/check.py). |
| DC-2 | Receive allocation | Preallocated buffers only | Every frame | D-1 | B-1 | Count allocations. |
"""


class ConstraintInventoryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.project = Path(self.temp.name) / "instrument"
        self.project.mkdir()
        self.put("architecture.md", ARCHITECTURE)
        self.put("contracts.md", "| ID | Boundary | Spec |\n|---|---|---|\n| X-1 | Register | — |\n"
                 "| X-2 | Receive | contracts/receive.md |\n")
        self.put("contracts/receive.md", "Observe the [allocation rule](../architecture.md#DC-2).\n")
        self.put("resource-math.md", """| ID | Assumption | Source |
|---|---|---|
| A-1 | Slots | DC-1 |

<!-- model:begin -->
**Design inputs**

| Input | Endpoint | Unit | Source |
|---|---|---|---|
| `DC-1` | `<= 16` | registrations | [DC-1](architecture.md#DC-1) |
<!-- model:end -->
""")
        self.put("resource-math/model.py", "# Memory estimate\n")
        self.put("data.md", "| ID | Entity | Meaning |\n|---|---|---|\n| E-1 | Registration | Active slot |\n")
        self.put("decisions.md", '<a id="D-1"></a>\n### D-1: Static buffers\n')
        self.put("requirements.md", '| ID | Constraint |\n|---|---|\n| C-1 | <a id="C-1"></a>Fixed memory |\n')
        self.put("mechanics.md", """# Mechanics
| ID | Mechanism |
|---|---|
| MC-1 | Receive |
| MC-2 | Independent |

### MC-1 Receive

Apply DC-2 on every error path.

### MC-2 Independent

No constraints here.
""")
        self.put("mechanics/check.py", "# Boundary model\n")

    def put(self, name, value):
        path = self.project / name
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text(value, encoding="utf-8")

    def cli(self, script, *options):
        result = subprocess.run([sys.executable, "-B", str(script), str(self.project), *options],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def inventory(self):
        self.cli(LINKER, "--anchors-only")
        self.cli(SCRIPTS / "design_inventory.py")
        return (self.project / "diagrams/DESIGN.md").read_text(encoding="utf-8")

    def card(self, markdown, rid):
        anchor = f'<a id="{rid}"></a>'
        self.assertEqual(markdown.count(anchor), 1)
        return markdown.split(anchor)[1].partition('<a id=')[0]

    def test_catalog_and_backlinks_survive_a_value_change(self):
        markdown = self.inventory()
        numeric = self.card(markdown, "DC-1")
        for text in ("Registrations", "≤ 16 registrations", "Across both ports", "[D-1](../decisions.md#D-1)",
                     "[C-1](../requirements.md#C-1)", "[boundary check](../mechanics/check.py)",
                     "[Source record](../architecture.md#DC-1)"):
            self.assertIn(text, numeric)
        for rid in ("B-1", "X-1", "E-1"):
            self.assertIn(f"[{rid}](#{rid})", numeric)
            self.assertIn("[DC-1](#DC-1)", self.card(markdown, rid))
        self.assertIn("[A-1](#A-1)", numeric)
        self.assertIn("[DC-1](#DC-1)", self.card(markdown, "A-1"))
        self.assertIn("Sizing calculation", numeric)
        self.assertIn("](../resource-math.md)", numeric)
        self.assertIn("](../resource-math/model.py)", numeric)
        qualitative = self.card(markdown, "DC-2")
        self.assertIn("Preallocated buffers only", qualitative)
        self.assertNotIn("Sizing calculation", qualitative)
        self.assertIn("[MC-1](#MC-1)", qualitative)
        self.assertIn("[X-2](#X-2)", qualitative)
        self.assertIn("[DC-2](#DC-2)", self.card(markdown, "X-2"))
        self.assertNotIn("MC-2", qualitative)
        mechanism = self.card(markdown, "MC-1")
        self.assertIn("[DC-2](#DC-2)", mechanism)
        self.assertIn("[Source record](../mechanics.md#MC-1)", mechanism)
        self.cli(SCRIPTS / "design_views.py", "--docs-base", "https://example.org/instrument/")
        view = (self.project / "diagrams/design.c4").read_text()
        self.assertIn("https://example.org/instrument/diagrams/DESIGN.md#DC-1", view)
        self.put("architecture.md", ARCHITECTURE.replace("≤ 16", "≤ 32"))
        updated = self.card(self.inventory(), "DC-1")
        self.assertIn("≤ 32 registrations", updated)
        self.assertNotIn("16 registrations", updated)

    def test_localized_reordered_columns_and_optional_section(self):
        self.put("architecture.md", """# Архитектура
| ID | Часть |
|---|---|
| B-1 | Контроллер |

## Проектные ограничения

| ИД | Проверка | Область действия | Параметр или правило | Применяется к | Основание | Допустимое значение |
|---|---|---|---|---|---|---|
| DC-7 | Проверить счётчик | На порт | Память | B-1 | D-1 | Только статическая |
""")
        card = self.card(self.inventory(), "DC-7")
        for value in ("Память", "На порт", "Только статическая", "Проверить счётчик", "[B-1](#B-1)"):
            self.assertIn(value, card)
        self.put("architecture.md", ARCHITECTURE.partition("## Design constraints")[0])
        md = self.inventory()
        self.assertNotIn("Design constraints", md)
        self.assertNotIn('<a id="MC-1">', md)

    def test_structured_contracts_cite_constraints(self):
        boundaries = ["| ID | Boundary | Spec |", "|---|---|---|"]
        for i, (ext, content) in enumerate((
            ("yaml", "description: Conforms to DC-2 # DC-1 is a draft\n"),
            ("yml", "# DC-1 was removed\ndescription: 'section #2 uses DC-2'\n"),
            ("json", '{"description": "Conforms to DC-2", "$comment": "DC-1 draft"}\n'),
        ), 5):
            path = f"contracts/boundary.{ext}"
            self.put(path, content)
            boundaries.append(f"| X-{i} | Receive | {path} |")
        self.put("contracts.md", "\n".join(boundaries) + "\n")
        md = self.inventory()
        for rid in ("X-5", "X-6", "X-7"):
            self.assertIn(f"[{rid}](#{rid})", self.card(md, "DC-2"))
            self.assertIn("[DC-2](#DC-2)", self.card(md, rid))
            self.assertNotIn("[DC-1](#DC-1)", self.card(md, rid))


if __name__ == "__main__":
    unittest.main()
