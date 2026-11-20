"""Exercise the optional local renderer, its asset cache and Markdown fallback."""
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills/flow/scripts"))
from preview_mermaid import MermaidPreview


class PreviewMermaidTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.site = self.root / "site"
        self.log = self.root / "renders"
        self.cli = self.root / "mmdc"
        self.cli.write_text(f"""#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv
assert args[args.index("-i") + 1] == "-"
config = json.loads(pathlib.Path(args[args.index("-c") + 1]).read_text())
assert config["securityLevel"] == "strict"
config = json.loads(pathlib.Path(args[args.index("-p") + 1]).read_text())
assert "--proxy-bypass-list=<-loopback>" in config["args"]
source = sys.stdin.read()
with open({str(self.log)!r}, "a") as log:
    print(source.strip(), file=log)
if source.startswith("invalid"):
    sys.exit(1)
output = '<html/>' if source.startswith("html") else '<svg xmlns="http://www.w3.org/2000/svg"/>'
pathlib.Path(args[args.index("-o") + 1]).write_text(output)
""")
        self.cli.chmod(0o700)

    def test_equal_diagrams_share_one_image_across_documents(self):
        renderer = MermaidPreview(self.site, self.cli)
        examples = "````markdown\n```mermaid\nignored\n```\n````\n"
        diagram = "stateDiagram-v2\n[*] --> ready\n"
        first = renderer.render(examples + "\n```mermaid\n" + diagram + "```\n")
        second = renderer.render("~~~mermaid\n" + diagram + "~~~\n")
        self.assertEqual(first, examples + "\n" + second)
        self.assertRegex(second, r"^!\[Mermaid diagram\]\(/docs/_mermaid/[a-f0-9]{64}\.svg\)\n$")
        images = list(self.site.rglob("*.svg"))
        self.assertEqual(len(images), 1)
        self.assertIn(images[0].name, second)
        self.assertEqual(self.log.read_text(), diagram)

    def test_absent_renderer_preserves_fences_and_warns_only_on_use(self):
        warnings = StringIO()
        with patch("preview_mermaid.shutil.which", return_value=None), redirect_stderr(warnings):
            renderer = MermaidPreview(self.site)
            plain = "```python\nprint('hello')\n```\n\n```mermaid\nunfinished"
            self.assertEqual(renderer.render(plain), plain)
            self.assertEqual(warnings.getvalue(), "")
            source = "~~~mermaid\r\ngraph TD\r\n~~~"
            self.assertEqual(renderer.render(source), source)
            self.assertEqual(renderer.render(source), source)
        self.assertEqual(warnings.getvalue().count("WARN:"), 1)
        self.assertFalse(self.site.exists())

    def test_failed_diagram_preserves_source_and_other_diagrams_render(self):
        renderer = MermaidPreview(self.site, self.cli)
        warnings = StringIO()
        with redirect_stderr(warnings):
            for source in ("invalid Mermaid", "html output"):
                fence = f"```mermaid\n{source}\n```\n"
                self.assertEqual(renderer.render(fence), fence)
                self.assertEqual(renderer.render(fence), fence)
            self.assertIn("/docs/_mermaid/", renderer.render("```mermaid\nerDiagram\n```"))
        self.assertEqual(self.log.read_text().splitlines(), ["invalid Mermaid", "html output", "erDiagram"])
        self.assertEqual(warnings.getvalue().count("WARN:"), 2)
        self.assertEqual(len(list(self.site.rglob("*.svg"))), 1)

    def test_explicit_missing_cli_has_actionable_error(self):
        with self.assertRaisesRegex(ValueError, "mmdc executable not found"):
            MermaidPreview(self.site, self.root / "absent")
