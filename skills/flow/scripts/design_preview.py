#!/usr/bin/env python3
"""Serve an offline LikeC4 build and its linked design documents on localhost."""
import argparse
from collections import deque
import errno
from functools import partial
from html import escape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import posixpath
import re
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit

from design_inventory import LINK, load_project, render_inventory
from design_views import generate
from preview_mermaid import MermaidPreview
from record_anchors import add_record_anchors, content_lines


DOCUMENTS = ("concept.md", "requirements.md", "decisions.md", "resource-math.md", "ux.md",
             "contracts.md", "data.md", "architecture.md", "high-level-design.md", "mechanics.md",
             "resilience.md", "roadmap.md")
# Tables also carry plain paths in Spec and Verified by cells.
ARTIFACT = re.compile(r"(?<![\w./-])(?:contracts|resource-math|mechanics|resilience|research|roadmap)/"
                      r"[^\s|`<>\[\]()*?#]+\.(?:md|yaml|yml|json|py)\b", re.I)
INVENTORY = Path("diagrams/DESIGN.md")
STYLE = """body{max-width:78rem;margin:2rem auto;padding:0 1.5rem;font:16px/1.55 system-ui,sans-serif}
h1,h2,h3{line-height:1.22}table{border-collapse:collapse;display:block;overflow-x:auto}
td,th{padding:.4rem .65rem;border:1px solid #bbb;text-align:left}pre{overflow-x:auto}
:target{scroll-margin-top:2rem}tr:has(:target){background:#fff3b0}nav{margin-bottom:2rem}"""


def executable(command, label, *, optional=False):
    path = shutil.which(command or label)
    if not command and not path and label in {"likec4", "mmdc"}:
        bundled = Path.home() / ".local/share/zkit/preview-tools/node_modules/.bin" / label
        path = shutil.which(str(bundled))
    if path:
        return os.path.abspath(path)
    if optional and not command:
        return None
    raise ValueError(f"{label} executable not found: {command or label}. Supply --{label} with its installed path.")


def run(args, *, cwd, source=None):
    result = subprocess.run(args, cwd=cwd, input=source, capture_output=True)
    if result.returncode:
        detail = (result.stderr or result.stdout).decode("utf-8", "replace").strip()
        raise ValueError(f"{Path(args[0]).name} failed ({result.returncode}): {detail}")
    return result.stdout


def read_project_file(directory, relative):
    """Read a regular file under the opened root, following no symlinks on any component."""
    fd = os.dup(directory)
    try:
        for part in relative.parts[:-1]:
            child = os.open(part, os.O_DIRECTORY | os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        handle = os.open(relative.name, os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=fd)
        with os.fdopen(handle, "rb") as stream:
            if stat.S_ISREG(os.fstat(handle).st_mode):
                return stream.read()
    except (FileNotFoundError, NotADirectoryError, IsADirectoryError):
        return None
    except OSError as error:
        if error.errno != errno.ELOOP:
            raise
    finally:
        os.close(fd)
    return None


def referenced_file(document, target):
    try:
        url = urlsplit(target.strip("<>"))
    except ValueError:
        return None
    path = unquote(url.path)
    if url.scheme or url.netloc or not path or path.startswith("/") or "\\" in path or "\x00" in path:
        return None
    relative = Path(posixpath.normpath(str(document.parent / path)))
    if any(part.startswith(".") for part in relative.parts) or relative == INVENTORY:
        return None
    if (relative == Path("resource_model.py") or relative.suffix.lower() == ".md"
            or (relative.parts[0] == "contracts" and relative.suffix.lower() in {".json", ".yaml", ".yml"})
            or (relative.suffix == ".py" and relative.parts[0] in {"mechanics", "resource-math", "resilience"})):
        return relative
    return None


def snapshot(project, target):
    queue = deque(map(Path, DOCUMENTS))
    seen = set()
    root = os.open(project, os.O_RDONLY | os.O_DIRECTORY)
    try:
        while queue:
            relative = queue.popleft()
            if relative in seen:
                continue
            seen.add(relative)
            data = read_project_file(root, relative)
            if data is None:
                continue
            dest = target / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            if relative.suffix != ".md":
                dest.write_bytes(data)
                continue
            source = data.decode("utf-8")
            if len(relative.parts) == 1:
                source = add_record_anchors(relative.name, source)
            dest.write_text(source, encoding="utf-8")
            targets = [match[2] for match in LINK.finditer(source)]
            targets.extend(ARTIFACT.findall(source))
            for address in targets:
                linked = referenced_file(relative, address)
                if linked is not None:
                    queue.append(linked)
    finally:
        os.close(root)


def separate_tables(markdown):
    """Older stage templates place the table header immediately after a paragraph."""
    lines = markdown.splitlines(keepends=True)
    for index, line in content_lines(lines):
        if index and index + 1 < len(lines) and line.lstrip().startswith("|") and lines[index - 1].strip():
            if re.fullmatch(r"\s*\|\s*:?-+:?\s*(?:\|\s*:?-+:?\s*)*\|?\s*", lines[index + 1]):
                lines[index] = "\n" + line
    return "".join(lines)


def build_preview(project, work, site, docs_url, likec4, pandoc, mmdc):
    sources = work / "records" / project.name
    sources.mkdir(parents=True)
    snapshot(project, sources)
    records = load_project(sources)
    inventory = sources / INVENTORY
    inventory.parent.mkdir(parents=True, exist_ok=True)
    inventory.write_text(render_inventory(records, inventory), encoding="utf-8")

    diagrams = work / "model"
    diagrams.mkdir()
    output = diagrams / "design.c4"
    model, warnings = generate(records, output, docs_url)
    for warning in warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    output.write_text(model, encoding="utf-8")
    run([likec4, "build", str(diagrams), "--output", str(site), "--base", "/",
         "--use-hash-history", "--no-app-config", "--no-build-webcomponent"], cwd=work)
    if not (site / "index.html").is_file():
        raise ValueError("LikeC4 build produced no index.html")
    mermaid = MermaidPreview(site, mmdc)
    for path in sorted(sources.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(sources)
        dest = site / "docs" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix != ".md":
            shutil.copyfile(path, dest)
            continue
        markdown = mermaid.render(path.read_text(encoding="utf-8"))
        body = run([pandoc, "--sandbox", "--from=gfm", "--to=html5", "--wrap=none"],
                   cwd=work, source=separate_tables(markdown).encode("utf-8")).decode("utf-8")
        title = escape(str(relative))
        html = (f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" '
                f'content="width=device-width,initial-scale=1"><title>{title}</title><style>{STYLE}</style>'
                '</head><body><nav><a href="/">Interactive diagrams</a> · '
                '<a href="/docs/diagrams/DESIGN.md">Design inventory</a></nav>' + body + '</body></html>')
        dest.write_text(html, encoding="utf-8")


class PreviewHandler(SimpleHTTPRequestHandler):
    def send_head(self):
        if self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            self.send_error(403)
            return None
        request_path = unquote(urlsplit(self.path).path)
        if "\x00" in request_path or any(part.startswith(".") for part in request_path.split("/")):
            self.send_error(404)
            return None
        path = Path(self.translate_path(self.path))
        if path.is_dir() and path != Path(self.directory):
            self.send_error(404)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)
        return None

    def guess_type(self, path):
        suffix = Path(path).suffix.lower()
        if suffix == ".md":
            return "text/html; charset=utf-8"
        if suffix in {".py", ".yml", ".yaml"}:
            return "text/plain; charset=utf-8"
        return super().guess_type(path)

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        # Project Markdown may contain authored HTML. It gets links and tables but no executable content.
        path = Path(self.translate_path(self.path))
        if path.is_relative_to(Path(self.directory) / "docs"):
            sandbox = "sandbox" if path.suffix == ".svg" else "sandbox allow-same-origin allow-popups allow-popups-to-escape-sandbox"
            self.send_header("Content-Security-Policy", "default-src 'none'; style-src 'unsafe-inline'; "
                             "img-src 'self' data:; base-uri 'none'; form-action 'none'; "
                             "frame-ancestors 'none'; " + sandbox)
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--port", type=int, default=0, help="loopback TCP port (default: allocate one)")
    parser.add_argument("--likec4", help="installed LikeC4 executable")
    parser.add_argument("--pandoc", help="installed Pandoc executable")
    parser.add_argument("--mmdc", help="installed Mermaid CLI for local SVGs (default: detect on PATH)")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("port must be from 0 to 65535")
    try:
        project = args.project.resolve(strict=True)
        if not project.is_dir():
            raise ValueError(f"project is not a directory: {project}")
        likec4 = executable(args.likec4, "likec4")
        pandoc = executable(args.pandoc, "pandoc")
        mmdc = executable(args.mmdc, "mmdc", optional=True)
        with tempfile.TemporaryDirectory(prefix="zkit-design-preview-") as directory:
            work = Path(directory)
            site = work / "site"
            handler = partial(PreviewHandler, directory=str(site))
            with ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
                base = f"http://127.0.0.1:{server.server_port}/"
                build_preview(project, work, site, base + "docs/", likec4, pandoc, mmdc)
                print(f"Preview: {base}", flush=True)
                server.serve_forever()
    except KeyboardInterrupt:
        return
    except (OSError, ValueError) as error:
        parser.exit(1, f"ERROR: {error}\n")


def stop(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, stop)
    main()
