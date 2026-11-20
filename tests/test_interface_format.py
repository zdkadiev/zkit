"""Run the architecture checker against project documents in both interface formats."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


CHECKER = Path(__file__).resolve().parents[1] / "skills/architecture/scripts/check_architecture.py"

REQUIREMENTS = """# Requirements
> **Status:** agreed · **Date:** 2026-11-20

| ID | Requirement | Priority |
|---|---|---|
| FR-1 | Display the latest sample | Must |
"""

ARCHITECTURE = """# Instrument
> **Based on:** requirements.md (2026-11-20)
> **Counts:** 3 B · {count} I · 3 S

## Parts
| ID | Part | Responsibility | Serves |
|---|---|---|---|
| B-1 | Sampler | Collect samples | FR-1 |
| B-2 | Controller | Accept new samples | FR-1 |
| B-3 | Display | Show fresh readings | FR-1 |

## C4
### Level 1 — Context
```mermaid
flowchart LR
    Operator --> Instrument
```
### Level 2 — Containers
```mermaid
flowchart LR
    B1 -->|I-1| B2
    B1 -->|I-1| B3
{arrows}```
### Level 3 — Components of B-2
```mermaid
flowchart LR
    Decode --> Accept
```

## Interfaces
{tables}

## Scenarios
| ID | Scenario | Steps | Outcome |
|---|---|---|---|
| S-1 | New reading | B-1 → I-1 → B-2 | Display receives accepted reading |
| S-2 | Restart | B-1 → I-1 → B-3 | Fresh samples resume |
| S-3 | Delayed sample | B-1 → I-1 → B-2 | Display keeps latest reading |

## Traceability
| Requirement | Covered by |
|---|---|
| FR-1 | B-1, B-2, B-3 |
"""

ENDS = "B-1 (publisher) → B-2, B-3 (recipients)"
FAN_OUT = ("I-1", ENDS, "Telemetry v1 over UART", "B-2 reads E-1 and updates E-2. B-3 reads E-2.", "FR-1")
STATELESS = ("I-2", "B-2 → B-3", "in-process health callback", "none", "FR-1")
HEADERS = ("ID", "From → to", "Protocol", "Entity effects", "Serves")
OLD_HEADERS = ("ID", "From → to", "Serves")


def table(headers, *rows):
    def line(cells):
        return "| " + " | ".join(cells) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *map(line, rows)])


def check(tables, count=1):
    arrows = "".join(f"    B2 -->|I-{n}| B3\n" for n in range(2, count + 1))
    design = ARCHITECTURE.format(count=count, arrows=arrows, tables=tables)
    with tempfile.TemporaryDirectory() as directory:
        project = Path(directory)
        (project / "architecture.md").write_text(design, encoding="utf-8")
        (project / "requirements.md").write_text(REQUIREMENTS, encoding="utf-8")
        return subprocess.run([sys.executable, "-B", str(CHECKER), directory], text=True, capture_output=True)


class InterfaceFormatTest(unittest.TestCase):
    def test_complete_fanout_and_stateless_exchanges(self):
        result = check(table(HEADERS, FAN_OUT, STATELESS), 2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARN", result.stdout)

    def test_legacy_warning_once_per_table(self):
        first = table(OLD_HEADERS, ("I-1", ENDS, "FR-1"), ("I-2", ENDS, "FR-1"))
        second = table(OLD_HEADERS, ("I-3", ENDS, "FR-1"))
        result = check(first + "\n\n" + second, 3)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        warnings = [line for line in result.stdout.splitlines() if line.startswith("WARN")]
        self.assertEqual(len(warnings), 2, result.stdout)
        for warning in warnings:
            self.assertIn("Protocol", warning)
            self.assertIn("Entity effects", warning)

    def test_partial_headers_name_missing_field(self):
        for missing in ("Protocol", "Entity effects"):
            with self.subTest(missing=missing):
                headers = [h for h in HEADERS if h != missing]
                cells = [v for h, v in zip(HEADERS, FAN_OUT) if h != missing]
                result = check(table(headers, cells))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertRegex(result.stdout, "ERROR[^\n]*" + missing)

    def test_partially_upgraded_table_is_invalid_even_before_its_first_exchange(self):
        empty = table(("ID", "From → to", "Protocol"))
        result = check(table(HEADERS, FAN_OUT) + "\n\n" + empty)
        self.assertEqual(result.returncode, 1, result.stdout)
        self.assertRegex(result.stdout, r"ERROR[^\n]*Entity effects")

    def test_missing_cells_name_interface_and_field(self):
        for index in (2, 3):
            with self.subTest(field=HEADERS[index]):
                invalid = list(STATELESS)
                invalid[index] = ""
                result = check(table(HEADERS, FAN_OUT, invalid), 2)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertRegex(result.stdout, "ERROR[^\n]*I-2[^\n]*" + HEADERS[index])

    def test_modeled_effect_identifies_its_participant_and_entity(self):
        for effect in ("reads E-1", "B-2 reads", "B-1 reads E-1", "B-2 E-1"):
            with self.subTest(effect=effect):
                invalid = (*STATELESS[:3], effect, "FR-1")
                result = check(table(HEADERS, FAN_OUT, invalid), 2)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertRegex(result.stdout, r"ERROR[^\n]*I-2[^\n]*Entity effects")

    def test_russian_columns_and_stateless_marker(self):
        headers = ("ID", "От → к", "Протокол", "Влияние на сущности", "Требования")
        result = check(table(headers, FAN_OUT, (*STATELESS[:3], "нет", "FR-1")), 2)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn("WARN", result.stdout)

    def test_linked_cells_use_visible_text_and_keep_escaped_pipe_inside_description(self):
        headers = ("ID", "Protocol", "What passes and why", "Entity effects", "From → to", "Serves")
        cells = ("I-1", "Telemetry v1", r"Read payload A\|B",
                 "[B-2](#B-2) accepts [E-2](#E-2)", "[B-1](#B-1) → [B-2](#B-2)", "FR-1")
        result = check(table(headers, cells))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("WARN", result.stdout)

    def test_versioned_protocol_can_name_its_technology(self):
        result = check(table(HEADERS, (*FAN_OUT[:2], "gRPC over HTTP/2", *FAN_OUT[3:])))
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertNotIn("technology words outside decisions", result.stdout)


if __name__ == "__main__":
    unittest.main()
