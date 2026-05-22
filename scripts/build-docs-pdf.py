"""Render docs/*.md as clean, print-friendly HTML, then let the caller convert to PDF.

Strips just-the-docs frontmatter, renders markdown with tables/fenced code, wraps each
page in a self-contained HTML with GitHub-flavored print CSS. Output goes to docs-pdf/html/.

Usage:
    uv run --with markdown --with pygments python scripts/build-docs-pdf.py

To produce PDFs (headless Chrome, macOS path shown — adjust for your OS):
    CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    for slug in index claude-code-quickstart getting-started sample-pipeline \\
                claude-code-guide git-workflow memory-page-template \\
                research-flow-docs; do
        "$CHROME" --headless --disable-gpu --no-pdf-header-footer \\
            --virtual-time-budget=10000 \\
            --print-to-pdf="docs-pdf/$slug.pdf" \\
            "file://$(pwd)/docs-pdf/html/$slug.html"
    done

`docs-pdf/` is gitignored — regenerate locally as needed.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown  # type: ignore[import-not-found]

REPO = Path(__file__).resolve().parents[1]
DOCS = REPO / "docs"
OUT = REPO / "docs-pdf" / "html"
OUT.mkdir(parents=True, exist_ok=True)

# Reading order
PAGES = [
    "index",
    "claude-code-quickstart",
    "pdf-to-agents-quickstart",
    "getting-started",
    "sample-pipeline",
    "claude-code-guide",
    "git-workflow",
    "memory-page-template",
]

CSS = """
@page { size: A4; margin: 18mm 16mm; }
html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.55;
  color: #1f2328;
  max-width: 780px;
  margin: 0 auto;
  padding: 0;
}
h1 { font-size: 22pt; border-bottom: 2px solid #d0d7de; padding-bottom: 6px; margin-top: 0; }
h2 { font-size: 16pt; border-bottom: 1px solid #d0d7de; padding-bottom: 4px; margin-top: 1.8em; }
h3 { font-size: 13pt; margin-top: 1.4em; }
h4 { font-size: 11.5pt; margin-top: 1.2em; }
p, ul, ol, table { margin: 0.6em 0; }
ul, ol { padding-left: 1.6em; }
a { color: #0969da; text-decoration: none; word-break: break-word; }
a:hover { text-decoration: underline; }
code {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Monaco, Consolas, monospace;
  font-size: 9.5pt;
  background: #f6f8fa;
  padding: 1px 4px;
  border-radius: 4px;
}
pre {
  background: #f6f8fa;
  border: 1px solid #d0d7de;
  border-radius: 6px;
  padding: 10px 12px;
  overflow: hidden;
  white-space: pre-wrap;
  word-break: break-word;
  page-break-inside: avoid;
  font-size: 9.5pt;
}
pre code { background: transparent; padding: 0; font-size: inherit; }
table { border-collapse: collapse; width: 100%; font-size: 10pt; }
th, td { border: 1px solid #d0d7de; padding: 6px 10px; text-align: left; vertical-align: top; }
th { background: #f6f8fa; }
blockquote { border-left: 3px solid #d0d7de; padding-left: 10px; color: #57606a; margin: 0.6em 0; }
hr { border: 0; border-top: 1px solid #d0d7de; margin: 2em 0; }
details {
  background: #f6f8fa; border: 1px solid #d0d7de; border-radius: 6px;
  padding: 6px 10px; margin: 0.6em 0;
}
summary { cursor: pointer; font-weight: 600; }
.page-break { page-break-before: always; }
h1, h2, h3, h4 { page-break-after: avoid; }
"""

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.DOTALL)
TOC_BLOCK = re.compile(r"<details[^>]*markdown=\"block\">.*?</details>", re.DOTALL)
TOC_LINE = re.compile(r"^\s*-\s*TOC\s*$\n^\s*\{:toc\}\s*$", re.MULTILINE)
ATTR_LIST = re.compile(r"\{:\s*\.[^}]*\}")

EXTENSIONS = [
    "fenced_code",
    "tables",
    "toc",
    "sane_lists",
    "attr_list",
    "def_list",
    "codehilite",
]


def render_one(slug: str) -> str:
    md_path = DOCS / f"{slug}.md"
    raw = md_path.read_text(encoding="utf-8")

    # Strip Jekyll frontmatter
    text = FRONTMATTER.sub("", raw)
    # Strip just-the-docs auto-TOC blocks (they're empty without Jekyll)
    text = TOC_BLOCK.sub("", text)
    text = TOC_LINE.sub("", text)
    # Strip just-the-docs attribute lists like {: .no_toc }
    text = ATTR_LIST.sub("", text)

    html_body = markdown.markdown(text, extensions=EXTENSIONS, output_format="html5")
    title = slug.replace("-", " ").title()

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>{CSS}</style>
</head>
<body>
{html_body}
</body>
</html>
"""


def render_combined() -> str:
    parts = []
    for i, slug in enumerate(PAGES):
        md_path = DOCS / f"{slug}.md"
        raw = md_path.read_text(encoding="utf-8")
        text = FRONTMATTER.sub("", raw)
        text = TOC_BLOCK.sub("", text)
        text = TOC_LINE.sub("", text)
        text = ATTR_LIST.sub("", text)
        body = markdown.markdown(text, extensions=EXTENSIONS, output_format="html5")
        sep = '<div class="page-break"></div>' if i > 0 else ""
        parts.append(sep + body)

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Research Flow — Documentation</title>
<style>{CSS}</style>
</head>
<body>
{"".join(parts)}
</body>
</html>
"""


def main() -> None:
    for slug in PAGES:
        out = OUT / f"{slug}.html"
        out.write_text(render_one(slug), encoding="utf-8")
        print(f"wrote {out.relative_to(REPO)}")

    combined = OUT / "research-flow-docs.html"
    combined.write_text(render_combined(), encoding="utf-8")
    print(f"wrote {combined.relative_to(REPO)}")


if __name__ == "__main__":
    main()
