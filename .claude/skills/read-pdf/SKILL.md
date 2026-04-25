---
name: read-pdf
description: Read a PDF by rendering each page to a PNG with PyMuPDF, then loading the images directly so Claude can see figures, tables, equations, and scanned text. Use when the user provides a PDF path/URL or asks to ingest a paper, report, or scanned document into research memory.
allowed-tools: Bash, Read, Write, Edit
---

# /read-pdf — Ingest a PDF as images

PyMuPDF text extraction loses figures, equations, multi-column layouts, and anything scanned. This skill renders each page to a PNG and lets the multimodal model read the page directly — same as how a human would read the paper.

## When to use
- User provides a `.pdf` path or URL
- User says "ingest this paper", "read this report", "summarize the figures in X.pdf"
- Text-only extraction would lose meaning (figures, equations, tables, scans)

For plain-text PDFs where you only need the text, `pymupdf`'s `page.get_text()` is faster — but the default for research ingestion is image rendering.

## Inputs to gather
1. **PDF path** (local file or URL — download URLs to `sources/` first)
2. **Page range** (optional, default = all). Format: `1-5,8,10-12` (1-indexed)
3. **Focus** (optional) — what to look for (architecture diagrams, results table, etc.)

## Workflow

### Step 1 — Ensure pymupdf is installed
```bash
uv add pymupdf  # only if not already in pyproject.toml
```

### Step 2 — If the PDF is a URL, download it into `sources/`
```bash
curl -L -o sources/<slug>.pdf "<url>"
```

Sources are immutable (enforced by `.claude/hooks/block-source-modification.sh`) — never edit a downloaded PDF after this step.

### Step 3 — Render to images
```bash
uv run python .claude/skills/read-pdf/scripts/pdf_to_images.py \
    sources/<slug>.pdf \
    --dpi 200 \
    [--pages 1-10]
```

Writes to `sources/_pdf-images/<slug>/<slug>-p001.png`, `…-p002.png`, … and prints paths to stdout.

**DPI guidance:**
- `150` — quick skim (small file size)
- `200` — default, good balance
- `300` — dense math/equations or fine-print scans

**Page selection:** for long papers, do the first pass at low DPI on all pages, then re-render specific pages of interest at 300 DPI.

### Step 4 — Read the images
Use the `Read` tool on each PNG path. Claude will see the page contents directly. For long documents, read in batches (5-10 pages at a time) and summarize before moving on, to avoid context bloat.

### Step 5 — Write into memory
Follow the standard ingest workflow (see `.claude/skills/analyze.md`):
- Create entity pages in `memory/entities/` for new concepts/people/methods
- Create finding pages in `memory/findings/` with `[<slug>]` source citations
- Note open questions in `memory/open-questions/`
- Update `memory/index.md` and append to `memory/log.md` (the post-memory-update hook will remind you)

## Citation convention
When citing a finding back to a specific page, use: `[<slug>:p<N>]` (e.g. `[attention-is-all-you-need:p4]`).

## Cleanup
Rendered PNGs in `sources/_pdf-images/` are derived artifacts — safe to regenerate. Add to `.gitignore` if you don't want them committed:
```
sources/_pdf-images/
```
(Check whether this is already excluded before adding.)

## Failure modes
- **`ModuleNotFoundError: pymupdf`** — run `uv add pymupdf && uv sync`
- **Garbled output / unreadable** — bump `--dpi` to 300
- **Huge PDF (>50 pages)** — always use `--pages` to scope; render-all will eat disk and tokens
- **Encrypted PDF** — pymupdf will raise; ask the user for the password or an unencrypted copy
