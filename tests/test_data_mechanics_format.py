"""Check entity, lifecycle and state tables through the public step checkers."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SKILLS = Path(__file__).resolve().parents[1] / "skills"
DATA = """# Data
> **Counts:** 1 E · 1 M · **Based on:** requirements.md (2026-11-20)

## Entity catalog
| ID | Entity | Meaning | Writers | Volume | Growth | Retention | Storage class | Sensitivity | Needs | Serves |
|---|---|---|---|---|---|---|---|---|---|---|
| E-1 | Registration | One activation | Operator | 16 B | 16 B per activation | Until removal | memory | internal | Unique identity | FR-1 |

## Relations
```mermaid
erDiagram
    E1
```

## Lifecycle and copies
| ID | Created by | Changed by | Deleted by / when | Copies | Copy lifetime |
|---|---|---|---|---|---|
| E-1 | Operator | Identity fixed | On removal | In-flight frames | Until receipt or loss |

## Memory strategy
| ID | Region | Contents | Lifetime | Size | Allocation | On exhaustion | Serves / limit |
|---|---|---|---|---|---|---|---|
| M-1 | Registry | Active E-1 | Process | 256 B | static | Refuse registration | FR-1 |
"""
FIELDS = """## Logical fields
| Entity | Field | Meaning and constraint |
|---|---|---|
| E-1 | registration ID | Never reused while frames carrying the old ID can arrive. |
"""
STATES = """## Entity states
<a id="E-1-reading-availability"></a>

**Entity:** E-1 · **Aspect:** reading availability · **Representation:** derived from existence of a current reading

| Value | Condition |
|---|---|
| awaiting_sample | No accepted sample exists. |
| has_reading | A current reading exists. |
"""
REQUIREMENTS = """| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Display readings | Must |
"""
MECHANICS = """# Mechanics
> **Counts:** 1 MC · **Based on:** requirements.md (2026-11-20), architecture.md (2026-11-20)

## Mechanisms
| ID | Part | Mechanism | Kind | Serves | Verified by | Risk |
|---|---|---|---|---|---|---|
| MC-1 | B-2 | Sample acceptance | state machine | FR-1 | review | M |

### MC-1 Sample acceptance
**Owner:** [B-2](architecture.md#B-2) · **Input:** [I-1](architecture.md#I-1) · **Subject:** [E-1 / reading availability](data.md#E-1-reading-availability)

Discard input for a retired registration before looking up the current reading in M-1.

| State | Event | Guard | Next state | Effects |
|---|---|---|---|---|
| awaiting_sample (initial) | sample | first | has_reading | Create reading |
| has_reading | sample | newer | has_reading | Update reading |
| has_reading | sample | equal or older | has_reading | Discard |
"""


def check(step, files):
    with tempfile.TemporaryDirectory() as directory:
        for name, content in files.items():
            (Path(directory) / name).write_text(content, encoding="utf-8")
        return subprocess.run(
            [sys.executable, "-B", str(SKILLS / step / "scripts" / f"check_{step}.py"), directory],
            capture_output=True, text=True,
        )


def check_data(data):
    return check("data", {"requirements.md": REQUIREMENTS, "data.md": data})


class DataFormatTest(unittest.TestCase):
    def test_translated_id_headers_keep_catalog_lifecycle_and_memory(self):
        for header in ("ИД", "Код", "Идентификатор"):
            with self.subTest(header=header):
                result = check_data(DATA.replace("| ID |", f"| {header} |"))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("1 entities, 1 memory regions", result.stdout)
                self.assertNotIn("WARN", result.stdout)

    def test_translated_requirement_header_keeps_reference_validation(self):
        result = check("data", {
            "requirements.md": REQUIREMENTS.replace("| ID |", "| ИД |"),
            "data.md": DATA.replace("FR-1", "FR-9"),
        })
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("E-1 serves FR-9, which is not in requirements", result.stdout)

    def test_legacy_catalog_without_fields_or_states(self):
        result = check_data(DATA)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARN", result.stdout)

    def test_duplicate_lifecycle_names_entity(self):
        data = DATA.replace("\n\n## Memory strategy", "\n| E-1 | Operator | Never | After 30 days | None | — |\n\n## Memory strategy")
        result = check_data(data)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("duplicate lifecycle row E-1", result.stdout)

    def test_fields_and_derived_aspect_do_not_define_catalog_entities(self):
        for heading in ("Entity catalog", "Entities", "Сущности"):
            with self.subTest(heading=heading):
                data = DATA.replace("## Entity catalog", STATES + "\n" + FIELDS + "\n## " + heading)
                if heading == "Сущности":
                    data = data.replace("Entity states", "Состояния сущностей").replace("Logical fields", "Логические поля")
                    data = data.replace("| Entity | Field | Meaning and constraint |", "| Сущность | Поле | Смысл и ограничение |")
                result = check_data(data)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("1 entities, 1 memory regions", result.stdout)
                self.assertNotIn("WARN", result.stdout)

    def test_field_must_belong_to_a_catalog_entity(self):
        for heading, column in (("Logical fields", "Entity"), ("Логические поля", "Сущность")):
            with self.subTest(heading=heading):
                fields = FIELDS.replace("Logical fields", heading).replace("| Entity |", f"| {column} |").replace("E-1", "E-9")
                result = check_data(DATA + fields)
                self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                self.assertIn("logical field references E-9", result.stdout)


def check_mechanics(mechanics):
    return check("mechanics", {
        "requirements.md": REQUIREMENTS,
        "data.md": DATA + STATES,
        "architecture.md": "| B-2 | Controller |\n| I-1 | Sample |\n",
        "mechanics.md": mechanics,
    })


class MechanicsFormatTest(unittest.TestCase):
    def test_translated_id_headers_keep_mechanisms(self):
        for header in ("ИД", "Код", "Идентификатор"):
            with self.subTest(header=header):
                result = check_mechanics(MECHANICS.replace("| ID |", f"| {header} |"))
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("1 mechanisms, 1 state machines", result.stdout)

    def test_machine_with_a_derived_subject_has_boundary_warnings(self):
        result = check_mechanics(MECHANICS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("1 state machines", result.stdout)
        warnings = [line for line in result.stdout.splitlines() if line.startswith("WARN")]
        self.assertEqual(len(warnings), 2, warnings)
        self.assertIn("'has_reading' has no way out", warnings[0])
        self.assertIn("no timeout / crash / failure event", warnings[1])

    def test_machine_rejects_undefined_transition_target(self):
        result = check_mechanics(MECHANICS.replace("first | has_reading", "first | stale_reading"))
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn("MC-1: transition goes to 'stale_reading'", result.stdout)


if __name__ == "__main__":
    unittest.main()
