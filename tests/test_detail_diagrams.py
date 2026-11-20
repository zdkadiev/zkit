from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/flow/scripts"
sys.path.insert(0, str(SCRIPTS))
from detail_diagrams import render_detail_diagrams


class DetailDiagramTest(unittest.TestCase):
    def render(self, data="", mechanics=""):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            if data:
                (path / "data.md").write_text(data, encoding="utf-8")
            if mechanics:
                (path / "mechanics.md").write_text(mechanics, encoding="utf-8")
            return render_detail_diagrams(path)

    def test_existing_er_fences_are_copied_and_examples_are_excluded(self):
        diagram = """~~~~mermaid
---
title: Регистрация
---
%% The source describes one optional reading
erDiagram
    E1 ||--o| E2 : "имеет"
~~~~"""
        data = "````markdown\n```mermaid\nerDiagram\n    Example\n```\n````\n" + diagram
        data += "\n\n```mermaid\nflowchart LR\nA --> B\n```\n"
        self.assertEqual(self.render(data=data), "### Entity relationships\n\n" + diagram)

    def test_sensor_branches_and_lifetime_match_the_authoritative_table(self):
        fixture = Path(__file__).parent / "fixtures/sensor"
        output = render_detail_diagrams(fixture)
        self.assertIn("erDiagram", output)
        self.assertIn("### MC-1 state transitions", output)
        self.assertIn('state "awaiting_sample" as St1', output)
        self.assertIn("[*] --> St1", output)
        self.assertEqual(output.count("St2 --> St2"), 2)
        self.assertIn("[Incoming sequence exceeds stored sequence]", output)
        self.assertIn("/ Discard frame. Preserve E-2.", output)
        self.assertNotIn("--> [*]", output)  # Removal happens outside this machine.

    def test_russian_headers_terminal_declarations_and_state_scope(self):
        table = """| Состояние | Событие | Условие | Следующее состояние | Действия |
|---|---|---|---|---|
| `Ждёт` (начальное) | сигнал | x < 1 | остаётся | обновить |
| Ждёт | конец | — | Готово | — |
| Готово (конечное) | — | — | — | ресурсы освобождены |
"""
        output = self.render(mechanics="## Механизмы\n### MC-8 Переход\n#### Таблица\n" + table
                             + "\n## Архив\n" + table)
        self.assertEqual(output.count("stateDiagram-v2"), 1)
        self.assertIn('state "Ждёт" as St1', output)
        self.assertIn("St1 --> St1 : сигнал<br/>[x #60; 1]<br/>/ обновить", output)
        self.assertIn("St2 --> [*]", output)
        self.assertNotIn("St2 --> St2", output)

    def test_fenced_examples_are_skipped_and_label_syntax_is_escaped(self):
        table = r"""| State | Event | Guard | Next state | Effects |
|---|---|---|---|---|
| Odd "name" | direction LR | x::y < 1 && z \| 3 | Idle | a; b |
| Idle (final) | — | — | — | — |
"""
        output = self.render(mechanics="````md\n### MC-9 example\n" + table + "````\n### MC-4 machine\n" + table)
        self.assertNotIn("MC-9", output)
        self.assertIn('state "Odd #34;name#34;" as St1', output)
        self.assertIn("#100;irection LR<br/>[x#58;#58;y #60; 1 #38;#38; z #124; 3]<br/>/ a#59; b", output)

    def test_unavailable_or_incomplete_sources_produce_no_views(self):
        self.assertEqual(self.render(), "")
        self.assertEqual(self.render(data="~~~mermaid\nerDiagram\nA", mechanics="### MC-1\n| State | Event |"), "")
        self.assertEqual(self.render(mechanics="### MC-1\n| State | Event | Next state |\n|---|---|---|\n| On |"), "")
