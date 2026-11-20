"""Exercise the optional LikeC4 reader through its CLI, without installing Node."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/flow/scripts/design_views.py"

ARCHITECTURE = """# Sensor instrument — Architecture

## 4. Parts
| ID | Part | Parent | Responsibility | Owns | Faces | Limits | Build / adopt / buy | Serves |
|---|---|---|---|---|---|---|---|---|
| B-1 | Sampler | — | Emits | — | X-1 | — | build | FR-1 |
| B-2 | Controller | — | Accepts samples | E-1 | — | — | build | FR-1 |
| B-3 | Screen | B-2 | Displays samples | — | — | — | build | FR-1 |

## 6. Interfaces
| ID | From → to | What passes and why | Style | Protocol | Entity effects | Delivery semantics | Serves |
|---|---|---|---|---|---|---|---|
| I-1 | B-1 (publisher) → B-2, B-3 | Sample | event | UART "v1" | B-2 updates E-1 under MC-1 | May drop | FR-1 |
| I-2 | B-1 → B-2 | Reset | sync | Register write | none | Acknowledged | FR-1 |

## 7. Key scenarios
| ID | Scenario | Steps (B-/I- ids) | Alternate path | Outcome against requirements | Gaps found |
|---|---|---|---|---|---|
| S-1 | Delayed frame | B-1 →I-1→ B-2; B-1 -> I-2 -> B-2 | B-1 → I-1 → B-3 | Keep latest sample | none |
| S-2 | Ambiguous order | B-1 or B-2 exchanges I-1 | — | — | — |
| S-3 | Wrong direction | B-2 → I-2 → B-1 | — | — | — |
"""


class DesignViewsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "sensor"
        self.root.mkdir()
        (self.root / "architecture.md").write_text(ARCHITECTURE, encoding="utf-8")
        (self.root / "data.md").write_text(
            "# Data\n| ID | Entity | Meaning |\n|---|---|---|\n| E-1 | Reading | Current |\n",
            encoding="utf-8")
        (self.root / "mechanics.md").write_text(
            "# Mechanics\n| ID | Mechanism |\n|---|---|\n| MC-1 | Sample acceptance |\n", encoding="utf-8")
        self.output = self.root / "diagrams" / "design.c4"

    def generate(self, *options):
        return subprocess.run([sys.executable, "-B", str(SCRIPT), str(self.root), *options],
                              capture_output=True, text=True)

    def test_model_keeps_hierarchy_parallel_edges_fanout_and_scenario_order(self):
        self.output.parent.mkdir()
        (self.output.parent / "DESIGN.md").write_text('# Inventory\n<a id="I-1"></a>\n', encoding="utf-8")
        result = self.generate("--docs-base", "https://example.org/sensor/")
        self.assertEqual(result.returncode, 0, result.stderr)
        model = self.output.read_text(encoding="utf-8")
        self.assertIn('relationship exchange { multiple true }', model)
        self.assertIn('view parts of project', model)
        self.assertIn('view scope_b2 of project.b2', model)
        self.assertIn('view between_b1_b2 {', model)
        self.assertIn('exclude * -> * where metadata.endpoints is not "between_b1_b2"', model)
        self.assertIn('project.b1 -[exchange]-> project.b2.b3 "I-1 Sample"', model)
        self.assertIn('project.b1 -[exchange]-> project.b2 "I-1 Sample"', model)
        self.assertIn('project.b1 -[exchange]-> project.b2 "I-2 Reset"', model)
        self.assertIn(r'technology "UART \"v1\""', model)
        self.assertIn('link https://example.org/sensor/diagrams/DESIGN.md#I-1', model)
        self.assertIn('link https://example.org/sensor/data.md', model)
        self.assertIn('link https://example.org/sensor/mechanics.md', model)
        self.assertIn('navigateTo scenario_s1', model)
        sequence = model.split('dynamic view scenario_s1 {')[1].split('dynamic view')[0]
        self.assertLess(sequence.index('-> project.b2 "I-1'), sequence.index('-> project.b2 "I-2'))
        self.assertIn('dynamic view scenario_s1_alt', model)
        for skipped in ('S-2', 'S-3'):
            self.assertIn(skipped, result.stderr)
            self.assertNotIn('dynamic view scenario_' + skipped.replace('-', '').lower(), model)

    def test_regeneration_and_file_ownership(self):
        target = self.root / "my reader" / "views.c4"
        result = self.generate("--output", str(target))
        self.assertEqual(result.returncode, 0, result.stderr)
        original = target.read_text(encoding="utf-8")
        self.assertIn("link ../architecture.md", original)
        self.assertNotIn("DESIGN.md", original)
        architecture = self.root / "architecture.md"
        architecture.write_text(ARCHITECTURE.replace("Sampler", "Transmitter").replace("UART", "SPI"),
                                encoding="utf-8")
        self.assertEqual(self.generate("--output", str(target)).returncode, 0)
        changed = target.read_text(encoding="utf-8")
        self.assertIn('b1 = part "B-1 Transmitter"', changed)
        self.assertIn('technology "SPI', changed)
        target.write_text("// Authored model\n", encoding="utf-8")
        result = self.generate("--output", str(target))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(target.read_text(encoding="utf-8"), "// Authored model\n")
        target.unlink()
        target.symlink_to(architecture)
        self.assertNotEqual(self.generate("--output", str(target)).returncode, 0)
        self.assertTrue(target.is_symlink())

    def test_ambiguous_endpoint_does_not_generate_arrows(self):
        path = self.root / "architecture.md"
        path.write_text(ARCHITECTURE.replace("B-1 → B-2 | Reset", "B-1 ↔ B-2 | Reset"),
                        encoding="utf-8")
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("I-2", result.stderr)
        self.assertNotIn('"I-2 Reset"', self.output.read_text(encoding="utf-8"))

    def test_link_existing_specs_and_http_urls_only(self):
        contracts = self.root / "contracts"
        contracts.mkdir()
        (contracts / "sensor.md").write_text("# Sensor protocol", encoding="utf-8")
        catalog = self.root / "mechanics.md"
        header = "| Interface | Spec |\n|---|---|\n"
        catalog.write_text(header + "| I-1 | in-process, X-1 payloads |\n"
                           "| I-2 | contracts/sensor.md |\n", encoding="utf-8")
        result = self.generate()
        self.assertEqual(result.returncode, 0, result.stderr)
        model = self.output.read_text(encoding="utf-8")
        self.assertNotIn("in-process", model)
        self.assertIn('link ../contracts/sensor.md "I-2 contract"', model)
        catalog.write_text(header + "| I-1 | https://example.org/sample |\n"
                           "| I-2 | https:malformed |\n", encoding="utf-8")
        self.assertEqual(self.generate().returncode, 0)
        model = self.output.read_text(encoding="utf-8")
        self.assertIn('link https://example.org/sample "I-1 contract"', model)
        self.assertNotIn("malformed", model)

    def test_cycle_fails_before_writing(self):
        (self.root / "architecture.md").write_text(
            ARCHITECTURE.replace("Controller | —", "Controller | B-3"), encoding="utf-8")
        result = self.generate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("B-2", result.stderr)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
