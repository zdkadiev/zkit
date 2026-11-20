"""Exercise the localhost preview through its public command and HTTP routes."""
from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/flow/scripts/design_preview.py"
SENSOR = ROOT / "tests/fixtures/sensor"
PANDOC = shutil.which("pandoc")
STUB = """#!/usr/bin/env python3
from pathlib import Path
import re
import sys
assert sys.argv[1] == "build" and "--use-hash-history" in sys.argv
output = Path(sys.argv[sys.argv.index("--output") + 1])
source = Path(sys.argv[2])
model = (source / "design.c4").read_text()
assert "http://127.0.0.1:" in model and "/docs/" in model
output.mkdir(parents=True, exist_ok=True)
(output / "index.html").write_text("<!doctype html><title>LikeC4 diagram viewer</title>")
"""


class DesignPreviewTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.project = self.root / "instrument"
        shutil.copytree(SENSOR, self.project)
        self.cli = self.root / "likec4"
        self.cli.write_text(STUB)
        self.cli.chmod(0o700)
        self.mmdc = self.root / "mmdc"
        self.mmdc.write_text("""#!/usr/bin/env python3
from pathlib import Path
import sys
Path(sys.argv[sys.argv.index("-o") + 1]).write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
""")
        self.mmdc.chmod(0o700)

    def command(self):
        return [sys.executable, "-B", str(SCRIPT), str(self.project), "--likec4", str(self.cli),
                "--mmdc", str(self.mmdc)]

    @contextmanager
    def server(self):
        process = subprocess.Popen(self.command(), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = process.stdout.readline()
            if not line.startswith("Preview: "):
                self.fail(line + process.stderr.read())
            yield line.split()[1]
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGTERM)
            process.communicate(timeout=10)

    @unittest.skipUnless(PANDOC, "preview integration requires local pandoc")
    def test_viewer_inventory_legacy_source_contracts_and_model(self):
        architecture = self.project / "high-level-design.md"
        (self.project / "architecture.md").rename(architecture)
        original = architecture.read_bytes()
        contracts = self.project / "contracts"
        (contracts / "register.yaml").write_text("version: 1\n")
        with (contracts / "register.md").open("a") as card:
            card.write("\n[Wire specification](register.yaml)\n")
            card.write("\nLegacy paragraph directly before a table.\n| Sensor | Unit |\n|---|---|\n| Sample | Celsius |\n")
        with self.server() as base:
            with urlopen(base, timeout=3) as response:
                self.assertIn("LikeC4", response.read().decode())
            with urlopen(base + "docs/diagrams/DESIGN.md", timeout=3) as response:
                self.assertIn("img-src 'self'", response.headers["Content-Security-Policy"])
                image = re.search(r'<img[^>]* src="(/docs/_mermaid/[^"]+\.svg)"', response.read().decode())
                self.assertIsNotNone(image)
            with urlopen(base + image[1].lstrip("/"), timeout=3) as response:
                self.assertEqual(response.headers.get_content_type(), "image/svg+xml")
                self.assertIn("sandbox", response.headers["Content-Security-Policy"])
            for path, anchor in (("high-level-design.md", "I-1"), ("mechanics.md", "MC-1"),
                                 ("data.md", "E-2"), ("diagrams/DESIGN.md", "B-2")):
                with urlopen(base + "docs/" + path + "#" + anchor, timeout=3) as response:
                    self.assertEqual(response.headers.get_content_type(), "text/html")
                    html = response.read().decode()
                    self.assertIn(f'id="{anchor}"', html)
                    self.assertIn("<table>", html)
            with urlopen(base + "docs/contracts/register.md") as response:
                card_html = response.read().decode()
                self.assertIn('href="register.yaml"', card_html)
                self.assertIn('<th>Unit</th>', card_html)
            for path, phrase in (("contracts/register.yaml", "version: 1"), ("resource-math/model.py", "ASSUMPTIONS")):
                with urlopen(base + "docs/" + path) as response:
                    self.assertEqual(response.headers.get_content_type(), "text/plain")
                    self.assertIn(phrase, response.read().decode())
        self.assertEqual(architecture.read_bytes(), original)
        self.assertFalse((self.project / "diagrams").exists())

    @unittest.skipUnless(PANDOC, "preview integration requires local pandoc")
    def test_serves_only_linked_project_artifacts_and_loopback_host(self):
        external = self.root / "other.md"
        external.write_text("outside contents")
        (self.project / "contracts" / "borrowed.md").symlink_to(external)
        (self.project / "private.md").write_text("local notes")
        (self.project / ".hidden.md").write_text("hidden notes")
        with (self.project / "contracts.md").open("a") as index:
            index.write("\n[Borrowed](contracts/borrowed.md) [Hidden](.hidden.md) [Outside](../other.md)")
        with self.server() as base:
            for path in ("docs/private.md", "docs/.hidden.md", "docs/contracts/borrowed.md",
                         "docs/../other.md", "docs/contracts/", "docs/%2e%2e/other.md"):
                with self.subTest(path=path), self.assertRaises(HTTPError) as context:
                    urlopen(base + path, timeout=3)
                self.assertEqual(context.exception.code, 404)
            with self.assertRaises(HTTPError) as context:
                urlopen(Request(base, headers={"Host": "untrusted.example"}), timeout=3)
            self.assertEqual(context.exception.code, 403)

    def test_reports_missing_executable(self):
        result = subprocess.run(self.command() + ["--likec4", str(self.root / "missing")], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("likec4", result.stderr.lower())
        self.assertNotIn("Traceback", result.stderr)

    @unittest.skipUnless(PANDOC, "preview integration requires local pandoc")
    def test_reports_failed_build_before_advertising_preview(self):
        self.cli.write_text("#!/bin/sh\necho 'invalid model' >&2\nexit 2\n")
        result = subprocess.run(self.command(), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid model", result.stderr)
        self.assertNotIn("Preview:", result.stdout)
