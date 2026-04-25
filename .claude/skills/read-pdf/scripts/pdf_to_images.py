#!/usr/bin/env python3
"""Render a PDF to PNG-per-page so Claude can read pages as images.

Usage:
    uv run python .claude/skills/read-pdf/scripts/pdf_to_images.py <pdf> [--out <dir>] [--dpi 200] [--pages 1-5]

Output:
    <out>/<pdf-stem>-p001.png, -p002.png, ...
    Default <out>: sources/_pdf-images/<pdf-stem>/
Prints written paths to stdout (one per line). Status to stderr.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymupdf


def parse_pages(spec: str | None, total: int) -> list[int]:
    if not spec:
        return list(range(total))
    out: set[int] = set()
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if "-" in chunk:
            a, b = chunk.split("-", 1)
            out.update(range(int(a) - 1, int(b)))
        else:
            out.add(int(chunk) - 1)
    return sorted(p for p in out if 0 <= p < total)


def convert(pdf_path: Path, out_dir: Path, dpi: int, pages: str | None) -> list[Path]:
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    doc = pymupdf.open(pdf_path)
    page_idxs = parse_pages(pages, doc.page_count)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    matrix = pymupdf.Matrix(dpi / 72, dpi / 72)
    written: list[Path] = []
    for i in page_idxs:
        pix = doc.load_page(i).get_pixmap(matrix=matrix, alpha=False)
        out = out_dir / f"{stem}-p{i + 1:03d}.png"
        pix.save(out)
        written.append(out)
    doc.close()
    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--dpi", type=int, default=200)
    ap.add_argument("--pages", type=str, default=None, help="e.g. '1-5,8,10-12' (1-indexed)")
    args = ap.parse_args()

    out_dir = args.out or Path("sources/_pdf-images") / args.pdf.stem
    written = convert(args.pdf, out_dir, args.dpi, args.pages)
    print(f"Wrote {len(written)} page(s) to {out_dir}/", file=sys.stderr)
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
