"""Exercise the sensor design through the same CLI entry points as the skills."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from urllib.parse import unquote


ROOT = Path(__file__).resolve().parents[1]


class SensorDesignTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name) / "sensor"
        shutil.copytree(ROOT / "tests/fixtures/sensor", self.project)

    def invoke(self, script, *args, expected=0):
        result = subprocess.run(
            [sys.executable, "-B", str(ROOT / "skills" / script), str(self.project), *args],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result.stdout

    def build(self):
        self.invoke("resource-math/scripts/check_resource_math.py", "--update")
        self.invoke("requirements/scripts/link_docs.py")
        for stage, checker in [
            ("resource-math", "resource_math"), ("contracts", "contracts"),
            ("data", "data"), ("architecture", "architecture"), ("mechanics", "mechanics"),
        ]:
            report = self.invoke(f"{stage}/scripts/check_{checker}.py")
            if stage == "mechanics":
                warnings = [line for line in report.splitlines() if line.startswith("WARN")]
                self.assertEqual(len(warnings), 2, report)
                self.assertIn("no way out", warnings[0])
                self.assertIn("no timeout / crash / failure", warnings[1])
            else:
                self.assertNotIn("WARN ", report)
        self.invoke("flow/scripts/design_inventory.py")
        self.invoke("flow/scripts/design_views.py")
        return (self.project / "diagrams/DESIGN.md").read_text()

    def test_sensor_drilldown_and_refresh(self):
        inventory = self.build()
        for record in ["I-1", "B-2", "E-2", "M-1", "MC-1", "L-1", "A-1", "X-1"]:
            self.assertIn(record, inventory)
        for fragment in ["Sensor telemetry v1 over UART", "800", "1200"]:
            self.assertIn(fragment, inventory)
        diagram = self.project / "diagrams/design.c4"
        self.assertIn("dynamic view", diagram.read_text())
        self.assertIn("Sensor telemetry v1 over UART", diagram.read_text())
        for link in re.findall(r'\]\(([^) ]+)\)', inventory):
            target, _, anchor = unquote(link).partition("#")
            if "://" in target:
                continue
            source = (self.project / "diagrams" / target) if target else self.project / "diagrams/DESIGN.md"
            self.assertTrue(source.is_file(), link)
            if re.fullmatch(r"(?:B|I|E|M|MC|X|S|L|A|DC)-\d+", anchor):
                self.assertIn(f'id="{anchor}"', source.read_text(), link)
        self.assertEqual(self.build(), inventory)
        model = self.project / "resource-math/model.py"
        model.write_text(model.read_text().replace('"expected": 800', '"expected": 850'))
        report = self.project / "resource-math.md"
        report.write_text(report.read_text().replace("| 400 | 800 | 1200 | assumed", "| 400 | 850 | 1200 | assumed"))
        self.assertIn("850", self.build())

    def test_changing_controller_limit_updates_all_views(self):
        original_inventory = self.build()
        self.assertIn("DC-1", original_inventory)
        self.assertIn("Preallocated memory only", original_inventory)
        report = self.project / "resource-math.md"
        self.assertRegex(report.read_text(), r"registration_memory\s*\| B \| 256 \|")
        arch = self.project / "architecture.md"
        self.assertEqual(arch.read_text().count("≤ 16 registrations"), 1)
        arch.write_text(arch.read_text().replace("≤ 16 registrations", "≤ 32 registrations"))
        inventory = self.build()
        self.assertIn("32 registrations", inventory)
        self.assertRegex(report.read_text(), r"registration_memory\s*\| B \| 512 \|")
        self.assertIn("../architecture.md#DC-1", (self.project / "contracts/register.md").read_text())

    def test_constraint_links_in_boundary_card(self):
        card = self.project / "contracts/register.md"
        original_text = "See DC-1. Preserve `DC-1` and [limit](../architecture.md#DC-1).\n"
        card.write_text(original_text)
        self.invoke("requirements/scripts/link_docs.py", "--anchors-only")
        self.assertEqual(original_text, card.read_text())
        self.invoke("requirements/scripts/link_docs.py")
        linked = card.read_text()
        self.assertIn("See [DC-1](../architecture.md#DC-1). Preserve `DC-1`", linked)
        self.invoke("requirements/scripts/link_docs.py")
        self.assertEqual(linked, card.read_text())
        card.write_text("Invalid reference DC-99.")
        self.assertIn("contracts/register.md", self.invoke("requirements/scripts/link_docs.py", expected=1))

    def test_protocol_required_on_modern_external_boundaries(self):
        p = self.project / "contracts.md"
        original = p.read_text()
        p.write_text(original.replace("contracts/register.md", "[Registration protocol](contracts/register.md)"))
        self.invoke("contracts/scripts/check_contracts.py")
        p.write_text(original.replace("| Registration procedure v1 |", "| — |"))
        self.assertIn("X-1", self.invoke("contracts/scripts/check_contracts.py", expected=1))
        p.write_text(original.replace("| Protocol ", "").replace("| Registration procedure v1 ", "")
                     .replace("| Sensor telemetry v1 over UART ", ""))
        self.invoke("contracts/scripts/check_contracts.py")

    def test_pre_mechanics_and_dangling_reference(self):
        architecture = self.project / "architecture.md"
        original = architecture.read_text()
        mechanics = self.project / "mechanics.md"
        complete = mechanics.read_text()
        mechanics.unlink()
        data = self.project / "data.md"
        data.write_text(data.read_text().replace("Governing mechanism: [MC-1 sample acceptance](mechanics.md#MC-1).", ""))
        architecture.write_text(original.replace(" under MC-1", ""))
        self.invoke("requirements/scripts/link_docs.py")
        mechanics.write_text(complete)
        architecture.write_text(original.replace("under MC-1", "under MC-99"))
        self.assertIn("MC-99", self.invoke("requirements/scripts/link_docs.py", expected=1))


if __name__ == "__main__":
    unittest.main()
