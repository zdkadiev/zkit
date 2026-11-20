"""Replace Mermaid fences with locally rendered SVG images in a preview copy of Markdown."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from xml.etree import ElementTree

from detail_diagrams import FENCE


class MermaidPreview:
    def __init__(self, site: Path, mmdc=None):
        self.directory = site.resolve() / "docs" / "_mermaid"
        binary = shutil.which(mmdc or "mmdc")
        if mmdc and not binary:
            raise ValueError(f"mmdc executable not found: {mmdc}")
        self.executable = os.path.abspath(binary) if binary else None
        self.images = {}
        self.warned_missing = False

    def render(self, markdown: str) -> str:
        """Keep ordinary Markdown and nested examples intact, including an unfinished fence."""
        lines = iter(markdown.splitlines(keepends=True))
        result = []
        for line in lines:
            opening = FENCE.match(line.rstrip("\r\n"))
            if not opening:
                result.append(line)
                continue
            marker, language = opening.groups()
            closing = re.compile(r"^ {0,3}" + marker[0] + "{" + str(len(marker)) + r",}\s*$")
            block = [line]
            for content in lines:
                block.append(content)
                if closing.fullmatch(content):
                    if language.strip().casefold() == "mermaid":
                        source = "".join(block[1:-1])
                        image = self._image(source)
                        if image:
                            ending = content[len(content.rstrip("\r\n")):]
                            block = [f"![Mermaid diagram](/docs/_mermaid/{image}){ending}"]
                    break
            result.extend(block)
        return "".join(result)

    def _image(self, source):
        if not self.executable:
            if not self.warned_missing:
                print("WARN: mmdc is unavailable; showing Mermaid source. Supply --mmdc to render SVGs.",
                      file=sys.stderr)
                self.warned_missing = True
            return None
        key = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if key in self.images:
            return self.images[key]

        filename = key + ".svg"
        try:
            with tempfile.TemporaryDirectory(prefix="zkit-mermaid-") as temp:
                work = Path(temp)
                (work / "mermaid.json").write_text('{"securityLevel":"strict"}', encoding="utf-8")
                # Keep Chromium's page offline, including destinations on the loopback interface.
                browser = {"args": ["--proxy-server=http://offline.invalid:80", "--proxy-bypass-list=<-loopback>",
                                    "--host-resolver-rules=MAP * ~NOTFOUND"]}
                chrome = os.environ.get("PUPPETEER_EXECUTABLE_PATH")
                system_chrome = Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                if chrome or (sys.platform == "darwin" and os.access(system_chrome, os.X_OK)):
                    browser["executablePath"] = chrome or str(system_chrome)
                (work / "browser.json").write_text(json.dumps(browser), encoding="utf-8")
                target = work / filename
                result = subprocess.run([self.executable, "-i", "-", "-o", str(target), "-c", "mermaid.json",
                                         "-p", "browser.json"], cwd=work, input=source, encoding="utf-8",
                                        errors="replace", capture_output=True, timeout=60)
                if result.returncode:
                    detail = (result.stderr or result.stdout).strip().splitlines()
                    raise ValueError(next((s for s in detail if s.strip()), f"exit {result.returncode}"))
                # Publish only an SVG. The viewer loads it via img; its document route restricts scripts.
                if ElementTree.parse(target).getroot().tag != "{http://www.w3.org/2000/svg}svg":
                    raise ValueError("mmdc output is not an SVG document")
                self.directory.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, self.directory / filename)
        except (OSError, ValueError, ElementTree.ParseError, subprocess.TimeoutExpired) as error:
            print(f"WARN: mmdc could not render diagram {key[:12]}; showing Mermaid source ({error}).",
                  file=sys.stderr)
            filename = None
        self.images[key] = filename
        return filename
