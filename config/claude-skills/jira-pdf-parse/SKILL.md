---
name: jira-pdf-parse
description: Extract Jira ticket data from a Jira PDF export into compact JSON, without loading the raw PDF text into context. Use when the user references a `jira-export-*.pdf` file (typically produced by Jira's "Export → PDF" for a filter or epic) and asks to summarize, prioritize, triage, or otherwise reason about the tickets inside. Skips resolved/closed tickets by default. Caches extracted text next to the PDF so re-runs are instant.
---

# jira-pdf-parse

## When to use

Trigger this skill whenever the user's request references a Jira PDF export and involves reasoning about the tickets inside — summarizing, prioritizing, comparing, searching, or filtering. Also trigger when the user pastes a path ending in `.pdf` that looks like a Jira export (filename usually contains `jira-export`, `DEX-`, or a ticket key).

Do NOT trigger for:
- PDFs that are not Jira exports (SAR dossiers, design docs, invoices, etc.) — those aren't structured this way.
- Single-ticket questions where the user has already pasted the ticket body into the chat.

## What it does

1. Runs `pdftotext -layout` on the PDF (installing `poppler` via `brew` if missing).
2. Caches the extracted text to `<pdf>.txt` next to the PDF so subsequent runs skip the conversion.
3. Splits the text on `[DEX-XXXX]` (or `[<PROJECT>-XXXX]`) headers into per-ticket blocks.
4. Extracts structured fields per ticket with regex: `key`, `title`, `status`, `priority`, `type`, `resolution`, `assignee`, `reporter`, `labels`, `components`, `parent`, `sprint`, `created`, `updated`, `resolved`.
5. Emits a compact JSON manifest to stdout — one object per ticket. Descriptions and comments are NOT included by default (that's what saves tokens); use `--detail <KEY>` to print a single ticket's full body when needed.

## Usage

```
python3 ~/.claude/skills/jira-pdf-parse/parse.py <pdf-path> [--include-resolved] [--detail DEX-XXXX]
```

Flags:
- `--include-resolved` — include Resolved/Closed tickets (default: skip them; most triage work is about the open set)
- `--detail KEY` — instead of the manifest, dump the raw text block for one ticket (description + comments + all fields)
- `--csv` — emit CSV instead of JSON (one row per ticket)
- `--force-reparse` — ignore the cached `.txt` and re-run `pdftotext`

## Output shape (JSON mode, default)

```json
[
  {
    "key": "DEX-22568",
    "title": "SHS HTTPRoute: strip inbound identity headers to prevent external-origin forgery",
    "status": "Open",
    "priority": "Must Do",
    "type": "Task",
    "resolution": "Unresolved",
    "assignee": "Szilárd Németh",
    "reporter": "Szilárd Németh",
    "components": "Taikun Integration",
    "labels": "DS-QBR, GA, SRC_DS_AWC_TAIKUN, ds-2.0-GA",
    "parent": "CDE 1.6-NEXT - Issues identified from Threat model sessions",
    "sprint": "",
    "created": "19/Jul/26",
    "updated": "31/Jul/26",
    "resolved": ""
  },
  ...
]
```

## Instructions to Claude

When the skill triggers:

1. **Do not `Read` the PDF directly** — `pdftotext` doesn't ship with the Read tool's PDF renderer and burns huge amounts of context. Always go through this parser.
2. **Do not `cat` or `Read` the raw `.txt` cache** except for the very small block of one specific ticket you need. The whole point is to avoid pulling the ~40k-token full-PDF text into context.
3. Run the parser and Read *its stdout output only* (which is 20× smaller). If the user asks about a specific ticket's full description or comments, re-run with `--detail DEX-XXXX`.
4. When the parser output is still too large (100+ tickets), pipe to `jq` to filter first — e.g. `jq '.[] | select(.status == "Open")'`.
5. Cache location: `<pdf>.txt` next to the PDF. Safe to delete; will be regenerated. Also creates `<pdf>.json` on request (via `--save-json` flag).

## Prerequisites

- `pdftotext` (from `poppler`) on PATH. Install: `brew install poppler`. The parser auto-installs if missing on macOS.
- Python 3.8+.

## Compose with `jira-prioritize`

The `jira-prioritize` skill invokes this one first, then applies a documented prioritization framework to the resulting manifest. If the user's request involves ranking or prioritization, prefer `jira-prioritize` — it handles the parse step internally.
