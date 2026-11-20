# Local interactive preview

Use the preview when a reader needs to follow an edge or a part from LikeC4 into the corresponding project record. The launcher uses Python 3, an installed LikeC4 CLI and Pandoc. The checked toolchain uses LikeC4 1.61.0, Pandoc 3.13 and Mermaid CLI 12.2.0. Explicit executable paths take precedence. By default, the launcher looks on PATH, then checks `~/.local/share/zkit/preview-tools/node_modules/.bin` for LikeC4 and Mermaid CLI. To render Mermaid ER, state and sequence diagrams as local SVGs, also provide an installed Mermaid CLI with its browser runtime. The launcher detects `mmdc` on PATH or accepts `--mmdc /path/to/mmdc`. Select a local Chromium executable with `PUPPETEER_EXECUTABLE_PATH` when needed. When it is unavailable, the preview keeps the Mermaid source blocks and reports that fallback.

```sh
python3 -B skills/flow/scripts/design_preview.py docs/zkit/<project>
```

For a toolchain installed in a project directory, pass its executable directly.

```sh
python3 -B skills/flow/scripts/design_preview.py docs/zkit/<project> \
  --likec4 ./node_modules/.bin/likec4 --pandoc /opt/homebrew/bin/pandoc
```

Open the printed loopback URL after the build finishes. The default port is allocated by the OS. Pass `--port 8123` for a fixed URL. LikeC4 views use hash routes. A source link opens the rendered document at its original Markdown path and ID, such as `/docs/data.md#E-2`. Every rendered document also links to the inventory and interactive diagrams.

The preview builds a snapshot of the stage documents, their referenced local Markdown, contract specs and models, including the older `high-level-design.md`. It adds record anchors in that snapshot and generates its own inventory and LikeC4 model. Referenced Python files are displayed as text. Files behind symlinks and hidden paths are omitted. The server binds only to IPv4 loopback. The build uses the locally installed tools.

Press Ctrl-C to stop the server and release its temporary files. Restart after editing project sources. Capacity figures come from the project's current resource-math report.
