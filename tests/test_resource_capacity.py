"""Exercise capacity comparisons through the resource-math checker and its generated Markdown."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "skills/resource-math/scripts/check_resource_math.py"

DOCUMENT = """# Resource math
> **Counts:** 3 A · 1 L
> **Verdict:** fits

| ID | Assumption | Evidence | Source |
|---|---|---|---|
| A-1 | Primary stream | known | Instrument specification |
| A-2 | Secondary stream | known | Instrument specification |
| A-3 | Receiver capacity | measured | Receiver timing run |

<!-- model:begin -->
<!-- model:end -->

| ID | Limit | Requirement |
|---|---|---|
| L-1 | Busy receiver | NFR-1 |
"""

MODEL = """
ASSUMPTIONS = {
    "A-1": {"best": 200, "expected": 600, "worst": 800},
    "A-2": {"best": 100, "expected": 200, "worst": 400},
    "A-3": {"best": 1000, "expected": 1000, "worst": 1000},
}
def compute(a):
    return {"total": a["A-1"] + a["A-2"], "maximum": a["A-3"], "one_flow": a["A-1"]}

UNITS = {"total": "frames/s", "maximum": "frames/s", "one_flow": "frames/s"}
LIMITS = [{"id": "L-1", "metric": "total", "op": "<=", "limit": 1000, "req": "NFR-1"}]
"""

RECEIVER = {
    "resource": "B-2 receiver",
    "interfaces": ["I-1", "X-2"],
    "windows": {"expected": "steady, 1 s", "worst": "burst, 1 s"},
    "demand": {"metric": "total", "basis": "estimated", "assumptions": ["A-1", "A-2"]},
    "capacity": {"metric": "maximum", "basis": "measured", "assumptions": ["A-3"]},
    "limits": ["L-1"],
}


class CapacityTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.document = self.project / "resource-math.md"
        self.document.write_text(DOCUMENT, encoding="utf-8")
        self.model = self.project / "resource-math/model.py"
        self.model.parent.mkdir()
        self.model.write_text(MODEL, encoding="utf-8")

    def with_entries(self, *entries, model=MODEL):
        self.model.write_text(model + f"\nCAPACITY = {list(entries)!r}\n", encoding="utf-8")

    def check(self, *args, code=0):
        result = subprocess.run([sys.executable, "-B", str(CHECK), str(self.project), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout + result.stderr

    def test_scenarios_share_one_receiver_and_refresh_from_model(self):
        self.with_entries(RECEIVER)
        self.check("--update")
        text = self.document.read_text()
        self.assertEqual(text.count("| B-2 receiver |"), 2)
        self.assertIn("I-1, X-2 | expected | steady, 1 s | 800 (estimated) | 1000 (measured) | frames/s | 80.00%", text)
        self.assertIn("worst | burst, 1 s | 1200 (estimated) | 1000 (measured) | frames/s | 120.00%", text)
        self.assertIn("demand [A-1](resource-math.md#A-1), [A-2](resource-math.md#A-2)", text)
        self.assertIn("capacity [A-3](resource-math.md#A-3) · [L-1](resource-math.md#L-1)", text)
        self.assertIn("[total, maximum](resource-math/model.py)", text)
        self.check()

        self.with_entries(RECEIVER, model=MODEL.replace('"expected": 600', '"expected": 700'))
        self.assertIn("block is stale", self.check(code=1))
        self.check("--update")
        self.assertIn("900 (estimated) | 1000 (measured) | frames/s | 90.00%", self.document.read_text())
        self.check()

    def test_unknown_capacity_and_zero_service_are_distinct(self):
        self.with_entries(
            {"resource": "link", "windows": {"expected": "1 s"},
             "demand": {"metric": "one_flow", "basis": "specified", "assumptions": ["A-1"]}},
            RECEIVER, model=MODEL.replace('"expected": 1000', '"expected": 0'),
        )
        self.check("--update")
        text = self.document.read_text()
        self.assertIn("600 (specified) | capacity unknown | frames/s | —", text)
        self.assertIn("800 (estimated) | 0 (measured) | frames/s | undefined (zero capacity)", text)

    def test_malformed_comparison_preserves_last_good_block(self):
        self.with_entries(RECEIVER)
        self.check("--update")
        last_good = self.document.read_bytes()
        invalid = [
            ("same unit", [RECEIVER], MODEL.replace('"maximum": "frames/s"', '"maximum": "bytes/s"')),
            ("finite non-negative", [RECEIVER], MODEL.replace('"maximum": a["A-3"]', '"maximum": -1')),
            ("combine shared demand", [RECEIVER, RECEIVER], MODEL),
            ("windows", [{**RECEIVER, "windows": {"burst": "1 s"}}], MODEL),
            ("invalid limits", [{**RECEIVER, "limits": ["L-9"]}], MODEL),
            ("invalid interfaces", [{**RECEIVER, "interfaces": ["B-2"]}], MODEL),
            ("capacity basis", [{**RECEIVER, "capacity": {**RECEIVER["capacity"], "basis": "guess"}}], MODEL),
            ("demand assumptions", [{**RECEIVER, "demand": {**RECEIVER["demand"], "assumptions": ["A-9"]}}], MODEL),
        ]
        for message, entries, model in invalid:
            with self.subTest(message=message):
                self.with_entries(*entries, model=model)
                self.assertIn(message, self.check("--update", code=1))
                self.assertEqual(last_good, self.document.read_bytes())

    def test_old_models_do_not_gain_a_capacity_section(self):
        self.check("--update")
        text = self.document.read_text()
        self.assertNotIn("Capacity by resource", text)
        self.with_entries()
        self.check()
        self.model.rename(self.project / "resource_model.py")
        self.check()
        self.assertEqual(self.document.read_text(), text)
