#!/usr/bin/env python3
"""
jira-pdf-parse — extract structured ticket data from a Jira PDF export.

See SKILL.md for full documentation. Short version:
  python3 parse.py <pdf> [--include-resolved] [--detail KEY] [--csv] [--force-reparse] [--save-json]
"""

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Jira PDF exports use a two-column layout for some lines
# (e.g. `Type: X   Priority: Y`, `Reporter: X   Assignee: Y`).
# Pattern approach: grab from label to either 2+ spaces (column break) OR end of line.
FIELD_PATTERNS = {
    "status": r"^\s*Status:\s+(\S[^\n]*?)\s*$",
    "priority": r"Priority:\s+([^\n]+?)\s*$",
    "type": r"^\s*Type:\s+(\S+?)(?:\s{2,}|\s*$)",
    "resolution": r"^\s*Resolution:\s+(\S[^\n]*?)(?:\s{2,}Votes:|\s*$)",
    "assignee": r"Assignee:\s+([^\n]+?)\s*$",
    "reporter": r"^\s*Reporter:\s+([^\n]+?)(?:\s{2,}Assignee:|\s*$)",
    "components": r"^\s*Components:\s+([^\n]+?)\s*$",
    "labels": r"^\s*Labels:\s+([^\n]+?)\s*$",
    "parent": r"^\s*Parent:\s+([^\n]+?)\s*$",
    "sprint": r"^\s*Sprint:\s+([^\n]*?)\s*$",
}

DATE_PATTERNS = {
    "created": r"Created:\s+(\d{1,2}/\w{3}/\d{2,4})",
    "updated": r"Updated:\s+(\d{1,2}/\w{3}/\d{2,4})",
    "resolved": r"Resolved:\s+(\d{1,2}/\w{3}/\d{2,4})",
}

HEADER_RE = re.compile(r"\[([A-Z][A-Z0-9]+-\d+)\]\s+(.*?)(?=\s+Created:|$)", re.DOTALL)


def ensure_pdftotext():
    if shutil.which("pdftotext"):
        return
    if sys.platform == "darwin" and shutil.which("brew"):
        print("Installing poppler via brew...", file=sys.stderr)
        subprocess.run(["brew", "install", "poppler"], check=True)
    else:
        raise SystemExit("pdftotext not found. Install poppler-utils (linux) or `brew install poppler` (mac).")


def extract_text(pdf_path: Path, force: bool) -> str:
    txt_cache = pdf_path.with_suffix(pdf_path.suffix + ".txt")
    if txt_cache.exists() and not force and txt_cache.stat().st_mtime >= pdf_path.stat().st_mtime:
        return txt_cache.read_text(encoding="utf-8", errors="replace")
    ensure_pdftotext()
    subprocess.run(["pdftotext", "-layout", str(pdf_path), str(txt_cache)], check=True)
    return txt_cache.read_text(encoding="utf-8", errors="replace")


def split_into_blocks(text: str):
    """
    Yield (key, title, body) tuples per ticket. A ticket header looks like:
        [DEX-22568] SHS HTTPRoute: strip ... Created: 19/Jul/26 Updated: 31/Jul/26
    Blocks may repeat (parent-epic banners); dedupe by (key, longest-body).
    """
    # Split on the header pattern
    parts = re.split(r"(?=\[[A-Z][A-Z0-9]+-\d+\])", text)
    seen = {}
    for part in parts:
        m = re.match(r"\[([A-Z][A-Z0-9]+-\d+)\]\s*(.*?)(?=\s+Created:|\n)", part, re.DOTALL)
        if not m:
            continue
        key = m.group(1)
        title = re.sub(r"\s+", " ", m.group(2)).strip()
        # Prefer the longest block for a given key (skip banner-only fragments)
        prev = seen.get(key)
        if prev is None or len(part) > len(prev[2]):
            seen[key] = (key, title, part)
    for v in seen.values():
        yield v


def extract_fields(block: str) -> dict:
    out = {}
    for name, pat in FIELD_PATTERNS.items():
        m = re.search(pat, block, re.MULTILINE)
        out[name] = m.group(1).strip() if m else ""
    for name, pat in DATE_PATTERNS.items():
        m = re.search(pat, block)
        out[name] = m.group(1).strip() if m else ""
    return out


def parse(pdf_path: Path, include_resolved: bool, force: bool):
    text = extract_text(pdf_path, force)
    rows = []
    for key, title, block in split_into_blocks(text):
        fields = extract_fields(block)
        if not include_resolved and fields.get("status", "").lower() in {"resolved", "closed", "done"}:
            continue
        rows.append({"key": key, "title": title, **fields})
    rows.sort(key=lambda r: r["key"])
    return rows


def detail(pdf_path: Path, target_key: str, force: bool):
    text = extract_text(pdf_path, force)
    for key, title, block in split_into_blocks(text):
        if key == target_key:
            return block
    return None


def main():
    ap = argparse.ArgumentParser(description="Parse a Jira PDF export into a compact ticket manifest.")
    ap.add_argument("pdf", type=Path)
    ap.add_argument("--include-resolved", action="store_true")
    ap.add_argument("--detail", metavar="KEY", help="Print the raw block for one ticket instead of the manifest")
    ap.add_argument("--csv", action="store_true")
    ap.add_argument("--force-reparse", action="store_true")
    ap.add_argument("--save-json", action="store_true", help="Also write <pdf>.json alongside stdout")
    args = ap.parse_args()

    if not args.pdf.exists():
        raise SystemExit(f"PDF not found: {args.pdf}")

    if args.detail:
        block = detail(args.pdf, args.detail, args.force_reparse)
        if block is None:
            raise SystemExit(f"Ticket {args.detail} not found in {args.pdf.name}")
        sys.stdout.write(block)
        return

    rows = parse(args.pdf, args.include_resolved, args.force_reparse)

    if args.csv:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        writer.writerows(rows)
    else:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")

    if args.save_json:
        args.pdf.with_suffix(args.pdf.suffix + ".json").write_text(
            json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(f"# parsed {len(rows)} tickets from {args.pdf.name}", file=sys.stderr)


if __name__ == "__main__":
    main()
