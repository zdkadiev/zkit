"""Architecture owns DC-n values, declaration sites and validation in both authoring languages."""
from decimal import Decimal
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest

SKILLS = Path(__file__).resolve().parents[1] / "skills"
sys.path.insert(0, str(SKILLS / "flow/scripts"))
from design_constraints import parse_design_constraints
from ids import rx
from record_anchors import add_record_anchors

HEADERS = ("ID", "Parameter or rule", "Allowed value", "Scope", "Basis", "Applies to", "Verification")
ROW = ("DC-1", "Registrations", "≤ 16 registrations", "Per controller across ports",
       "Bounded storage", "B-1", "Register across two ports and reject the first excess request.")
ARCHITECTURE = """# Instrument
> **Counts:** 1 B · 0 I · 1 S

## Parts
| ID | Part | Responsibility | Serves |
|---|---|---|---|
| B-1 | Controller | Keep accepted registrations | FR-1 |

## C4
### Level 1 — Context
```mermaid
flowchart LR
    Client --> Instrument
```
### Level 2 — Containers
```mermaid
flowchart LR
    B1["B-1 Controller"]
```

## Scenarios
| ID | Scenario | Steps | Outcome |
|---|---|---|---|
| S-1 | Full | B-1 rejects the registration | Keep active registrations |

## Traceability
| Requirement | Covered by |
|---|---|
| FR-1 | B-1 |
"""


def catalog(*rows, headers=HEADERS, title="Design constraints"):
    def line(values):
        return "| " + " | ".join(values) + " |\n"
    return "## " + title + "\n" + line(headers) + line(["---"] * len(headers)) + "".join(map(line, rows))


def run(script, project, *args):
    return subprocess.run([sys.executable, "-B", str(SKILLS / script), str(project), *args],
                          text=True, capture_output=True)


class DesignConstraintTest(unittest.TestCase):
    def test_numeric_endpoint_syntax(self):
        cases = {
            "16 registrations": (16, 16, True, True, "registrations"),
            "= 1.25 KiB/s": (Decimal("1.25"), Decimal("1.25"), True, True, "KiB/s"),
            "≤ 16 registrations": (None, 16, False, True, "registrations"),
            "> -3 °С": (-3, None, False, False, "°С"),
            ">= 2.5e2 1/s": (250, None, True, False, "1/s"),
            "< 80%": (None, 80, False, False, "%"),
            "[-4, 16) ms": (-4, 16, True, False, "ms"),
            "(-4, 16] ms": (-4, 16, False, True, "ms"),
            "(0, 1) ratio": (0, 1, False, False, "ratio"),
            "[0, 0] slots": (0, 0, True, True, "slots"),
        }
        for allowed, expected in cases.items():
            with self.subTest(allowed=allowed):
                records, errors = parse_design_constraints(catalog((*ROW[:2], allowed, *ROW[3:])))
                self.assertEqual(errors, [])
                bound = records["DC-1"].numeric
                self.assertEqual((bound.lower, bound.upper, bound.lower_inclusive, bound.upper_inclusive, bound.unit), expected)

    def test_malformed_numeric_values_and_ambiguous_ranges_fail(self):
        for value in ("16", "≤ 16", "16..32 slots", "16 to 32 slots", "[0, 16]", "[1, 0] slots",
                      "(1, 1] slots", "10 slots - 20 slots", "10 slots-20 slots", "10 slots..20 slots", "**≤ 16**", "at most 16 registrations", "≈ 2 slots",
                      ">= NaN slots", "≤ sixteen slots", "[0, 16 ms", "<= 2 3"):
            with self.subTest(value=value):
                records, errors = parse_design_constraints(catalog((*ROW[:2], value, *ROW[3:])))
                self.assertFalse(records)
                self.assertTrue(any("DC-1" in msg and "numeric" in msg for msg in errors), errors)

    def test_qualitative_rule_and_localized_reordered_columns(self):
        headers = ("ИД", "Проверка", "Допустимое значение", "Область действия", "Применяется к",
                   "Параметр или правило", "Основание")
        rule = "Использовать заранее выделенную память после фазы 2"
        row = ("DC-2", "Ноль выделений на каждом пути", rule, "Приём сообщений", "B-1",
               "Память обработчика", "Предсказуемая задержка")
        source = catalog(row, headers=headers, title="3.1 Проектные ограничения")
        records, errors = parse_design_constraints(source)
        self.assertEqual(errors, [])
        record = records["DC-2"]
        self.assertIsNone(record.numeric)
        self.assertEqual((record.parameter, record.allowed_value, record.basis), (row[5], rule, row[6]))
        anchored = add_record_anchors("architecture.md", source)
        self.assertIn('<a id="DC-2"></a>Память обработчика', anchored)
        self.assertEqual(parse_design_constraints(anchored), (records, []))
        self.assertEqual(add_record_anchors("architecture.md", anchored), anchored)

    def test_missing_fields_partial_tables_and_duplicate_ids(self):
        for i, header in enumerate(HEADERS):
            with self.subTest(header=header):
                headers = [h for j, h in enumerate(HEADERS) if j != i]
                values = [v for j, v in enumerate(ROW) if j != i]
                records, errors = parse_design_constraints(catalog(values, headers=headers))
                self.assertFalse(records)
                self.assertIn(header, " ".join(errors))
        for i, field in enumerate(HEADERS[1:], start=1):
            with self.subTest(field=field):
                values = list(ROW)
                values[i] = "—"
                records, errors = parse_design_constraints(catalog(values))
                self.assertFalse(records)
                self.assertIn(field, " ".join(errors))
        for text, detail in (
                (catalog((*ROW[:-1],)), "cells"),
                (catalog(("C-1", *ROW[1:])), "expected DC-n"),
                (catalog((*ROW[:5], "controller", ROW[-1])), "Applies to"),
                (catalog(ROW) + "\n" + catalog(ROW), "duplicate design constraint DC-1"),
                (catalog(), "no DC-n rows"),
                (catalog(ROW).replace("---", "?", 1), "separator"),
                (catalog(ROW + ("extra",), headers=HEADERS + ("Основание",)), "duplicate catalog column"),
                ("## Design constraints\n\n", "missing catalog table")):
            with self.subTest(detail=detail):
                records, errors = parse_design_constraints(text)
                self.assertFalse(records)
                self.assertIn(detail, " ".join(errors))

    def test_ownership_and_stable_anchors(self):
        sample = catalog(ROW)
        other = sample.replace("## Design constraints", "## Traceability") + "### DC-1: Other mention\n"
        source = "````md\n" + sample + "````\n\n" + other + "\n" + sample
        for name in ("architecture.md", "high-level-design.md"):
            anchored = add_record_anchors(name, source)
            self.assertEqual(anchored.count('<a id="DC-1"></a>'), 1)
            self.assertIn('<a id="DC-1"></a>Registrations', anchored.split("### DC-1: Other mention")[1])
            self.assertEqual(add_record_anchors(name, anchored), anchored)
            edited = anchored.replace("≤ 16 registrations", "≤ 32 registrations").replace("Registrations", "Active subscriptions")
            self.assertEqual(add_record_anchors(name, edited), edited)
            self.assertEqual(parse_design_constraints(edited)[0]["DC-1"].numeric.upper, 32)
        retired = add_record_anchors("architecture.md", sample).replace("## Design constraints", "## Old tables")
        self.assertNotIn('<a id="DC-1"></a>', add_record_anchors("architecture.md", retired))
        self.assertEqual(add_record_anchors("contracts.md", sample), sample)
        self.assertEqual(parse_design_constraints(other), ({}, []))

    def test_checker_and_linker_use_canonical_definition(self):
        check = "architecture/scripts/check_architecture.py"
        link = "requirements/scripts/link_docs.py"
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            path = project / "architecture.md"
            path.write_text(ARCHITECTURE)
            self.assertEqual(run(check, project).returncode, 0)
            path.write_text(ARCHITECTURE + "\n" + catalog(ROW))
            self.assertEqual(run(check, project).returncode, 0)
            (project / "requirements.md").write_text(
                "| ID | Requirement | Priority |\n|---|---|---|\n| FR-1 | Read | Must |\n| C-1 | Input | Must |\n")
            contracts = project / "contracts.md"
            contracts.write_text("# Contracts\nC-1 and DC-1.\n")
            linked = run(link, project)
            self.assertEqual(linked.returncode, 0, linked.stdout + linked.stderr)
            self.assertIn('<a id="DC-1"></a>Registrations', path.read_text())
            contracts.write_text("# Contracts\nC-1 and DC-99.\n")
            # A local heading, a projection and a row in an unrelated table cannot define a DC.
            path.write_text(path.read_text() + "\n## Notes\n### DC-99 Other\n| ID | Parameter or rule |\n|---|---|\n| DC-99 | Other |\n")
            (project / "old_model.py").write_text('bounds = {"DC-99": 1}\n')
            linked = run(link, project)
            self.assertEqual(linked.returncode, 1, linked.stdout + linked.stderr)
            self.assertRegex(linked.stdout, r"DC-99.*not defined in architecture.md")
            self.assertNotIn('<a id="DC-99"></a>', path.read_text())
            path.write_text(ARCHITECTURE.replace("Keep accepted registrations | FR-1", "Keep accepted registrations | DC-1")
                            + "\n" + catalog(ROW).replace("≤ 16 registrations", "≤ 16"))
            result = run(check, project)
            self.assertEqual(result.returncode, 1)
            self.assertIn("DC-1", result.stdout)
            self.assertIn("unit", result.stdout)
            self.assertIn("B-1 serves no requirement", result.stdout)

    def test_requirement_matching_preserves_ranges_without_matching_dc(self):
        self.assertEqual(re.findall(rx("FR", "NFR", "C"), "DC-1 C-2…C-5 FR-3–NFR-4 MC-6"),
                         ["C-2", "C-5", "FR-3", "NFR-4"])


if __name__ == "__main__":
    unittest.main()
