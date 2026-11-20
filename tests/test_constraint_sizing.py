"""Run resource sizing against architecture-owned bounds and early workload assumptions."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECK = Path(__file__).resolve().parents[1] / "skills/resource-math/scripts/check_resource_math.py"
MODEL = """
ASSUMPTIONS = {"A-1": {"label": "Pilot registrations", "unit": "registrations",
                       "best": 2, "expected": 3, "worst": 4}}
DESIGN_INPUTS = {"DC-1": {"unit": "registrations", "op": "<=", "provisional": "A-1"}}
UNITS = {"slot_memory": "bytes"}
def compute(a):
    return {"slot_memory": a["DC-1"] * 64}
LIMITS = [{"id": "L-1", "metric": "slot_memory", "op": "<=", "limit": 4096, "req": "NFR-1"}]
"""
DOC = """# Resource math
> **Counts:** 1 A · 1 L
> **Verdict:** fits

| ID | Assumption | Evidence | Source |
|---|---|---|---|
| A-1 | Pilot registrations | known | Pilot workload |

<!-- model:begin -->
<!-- model:end -->

| ID | Limit | Requirement |
|---|---|---|
| L-1 | Slot memory | NFR-1 |
"""
ARCHITECTURE = """# Architecture

## Design constraints

| ID | Parameter or rule | Allowed value | Scope | Basis | Applies to | Verification |
|---|---|---|---|---|---|---|
| DC-1 | Active registrations | ≤ 16 registrations | Across the controller ports | D-1 | L-1 | Fill slots across both ports. |
"""


class ConstraintSizingTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.project = Path(temp.name)
        self.document = self.project / "resource-math.md"
        self.document.write_text(DOC)
        self.model = self.project / "resource-math/model.py"
        self.model.parent.mkdir()
        self.model.write_text(MODEL)
        self.owner = self.project / "architecture.md"

    def check(self, *args, code=0):
        result = subprocess.run([sys.executable, "-B", str(CHECK), str(self.project), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        return result.stdout + result.stderr

    def test_owner_edit_recalculates_fixed_slots_without_editing_model(self):
        self.owner.write_text(ARCHITECTURE)
        self.check("--update")
        self.assertIn("| slot_memory | bytes | 1024 | 1024 | 1024 |", self.document.read_text())
        self.assertIn("[DC-1](architecture.md#DC-1)", self.document.read_text())
        self.owner.write_text(ARCHITECTURE.replace("16 registrations", "32 registrations"))
        self.assertIn("block is stale", self.check(code=1))
        self.check("--update")
        self.assertIn("| slot_memory | bytes | 2048 | 2048 | 2048 |", self.document.read_text())
        self.assertEqual(self.model.read_text(), MODEL)
        self.check()

    def test_early_provisional_uses_each_scenario_and_sensitivity_then_reconciles(self):
        self.check("--update")
        report = self.document.read_text()
        self.assertIn("Provisional [A-1](resource-math.md#A-1)", report)
        self.assertIn("| slot_memory | bytes | 128 | 192 | 256 |", report)
        self.assertIn("| A-1 | L-1 | +33% |", report)
        self.owner.write_text(ARCHITECTURE)
        self.assertIn("block is stale", self.check(code=1))
        self.check("--update")
        self.assertNotIn("Provisional", self.document.read_text())
        self.assertNotIn("| A-1 | L-1 | +33% |", self.document.read_text())

    def test_invalid_canonical_reference_fails_even_with_provisional_input(self):
        self.owner.write_text(ARCHITECTURE)
        self.check("--update")
        good = self.document.read_bytes()
        for edit, error in [
            (("DC-1", "DC-2"), "unknown DC-1"),
            (("≤ 16 registrations", "Preallocated memory only"), "qualitative"),
            (("≤ 16 registrations", "< 16 registrations"), "endpoint"),
            (("≤ 16 registrations", "≥ 16 registrations"), "endpoint"),
            (("≤ 16 registrations", "≤ 16 bytes"), "unit mismatch"),
        ]:
            with self.subTest(error=error, edit=edit):
                self.owner.write_text(ARCHITECTURE.replace(*edit))
                self.assertIn(error, self.check("--update", code=1))
                self.assertEqual(self.document.read_bytes(), good)

    def test_missing_owner_requires_explicit_compatible_fallback(self):
        for model, error in [
            (MODEL.replace(', "provisional": "A-1"', ""), "explicit provisional"),
            (MODEL.replace('"provisional": "A-1"', '"provisional": "A-8"'), "explicit provisional"),
            (MODEL.replace('"unit": "registrations"', '"unit": "bytes"', 1), "unit mismatch"),
        ]:
            with self.subTest(error=error):
                self.model.write_text(model)
                self.assertIn(error, self.check("--update", code=1))
                self.assertEqual(self.document.read_text(), DOC)

    def test_exact_values_and_range_endpoints_respect_the_model_operator(self):
        model = (MODEL.replace("registrations", "ms").replace("slot_memory", "boundary")
                 .replace("bytes", "ms").replace('a["DC-1"] * 64', 'a["DC-1"]'))
        for allowed, op, value in [
            ("= 4 ms", "=", 4),
            ("(1, 5] ms", ">", 1),
            ("(1, 5] ms", "<=", 5),
            ("[0, 3.5) ms", "<", 3.5),
            ("[0, 3.5) ms", ">=", 0),
        ]:
            with self.subTest(allowed=allowed, op=op):
                self.owner.write_text(ARCHITECTURE.replace("≤ 16 registrations", allowed))
                self.model.write_text(model.replace('"op": "<="', f'"op": "{op}"', 1))
                self.check("--update")
                self.assertIn(f"| boundary | ms | {value} | {value} | {value} |", self.document.read_text())

    def test_tightening_range_to_singleton_preserves_both_endpoint_selectors(self):
        for op, before in [(">=", 64), ("<=", 256)]:
            with self.subTest(op=op):
                self.model.write_text(MODEL.replace('"op": "<="', f'"op": "{op}"', 1))
                self.owner.write_text(ARCHITECTURE.replace("≤ 16", "[1, 4]"))
                self.check("--update")
                self.assertIn(f"| slot_memory | bytes | {before} | {before} | {before} |", self.document.read_text())
                self.owner.write_text(ARCHITECTURE.replace("≤ 16", "[4, 4]"))
                self.check("--update")
                self.assertIn("| slot_memory | bytes | 256 | 256 | 256 |", self.document.read_text())
                self.owner.write_text(ARCHITECTURE.replace("≤ 16", "= 4"))
                self.assertIn("endpoint", self.check("--update", code=1))

    def test_legacy_owner_and_legacy_model_without_any_constraint_input(self):
        legacy = self.project / "high-level-design.md"
        legacy.write_text(ARCHITECTURE)
        self.check("--update")
        self.assertIn("[DC-1](high-level-design.md#DC-1)", self.document.read_text())
        self.model.write_text("\n".join(line for line in MODEL.replace('a["DC-1"]', 'a["A-1"]').splitlines()
                                        if not line.startswith("DESIGN_INPUTS")))
        self.model.rename(self.project / "resource_model.py")
        self.check("--update")
        self.assertNotIn("Design inputs", self.document.read_text())
        self.check()
