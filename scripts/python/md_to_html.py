#!/usr/bin/env python3
"""Convert one or more Markdown files to self-contained HTML files.

Usage examples:
  # Single file → html-export/ next to it
  python3 md_to_html.py notes.md

  # Multiple files → custom output dir
  python3 md_to_html.py *.md --output-dir /tmp/review

  # All *.md files in a directory, open each in the browser after export
  python3 md_to_html.py --input-dir ./investigation-breakdown --open

  # Prefix output filenames (useful for Jira comment ordering)
  python3 md_to_html.py comment-1.md comment-2.md --prefix jira-
"""

import subprocess
import sys
import webbrowser
from pathlib import Path

import click

try:
    import markdown
except ImportError:
    click.secho("Error: 'markdown' package not found. Install with: pip install markdown", fg="red", err=True)
    sys.exit(1)

_CSS = """
<style>
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    max-width: 980px;
    margin: 40px auto;
    padding: 0 24px;
    color: #1a1a1a;
    line-height: 1.65;
  }
  h1 { border-bottom: 2px solid #ccc; padding-bottom: 8px; }
  h2 { border-bottom: 1px solid #e0e0e0; padding-bottom: 4px; margin-top: 36px; }
  h3 { margin-top: 24px; }
  code {
    background: #f5f5f5;
    padding: 2px 5px;
    border-radius: 3px;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    font-size: 0.875em;
  }
  pre {
    background: #f5f5f5;
    padding: 14px 16px;
    border-radius: 5px;
    overflow-x: auto;
    border: 1px solid #e0e0e0;
  }
  pre code { background: none; padding: 0; font-size: 0.875em; }
  table { border-collapse: collapse; width: 100%; margin: 12px 0; }
  th, td { border: 1px solid #d0d0d0; padding: 7px 12px; text-align: left; vertical-align: top; }
  th { background: #f0f0f0; font-weight: 600; }
  tr:nth-child(even) { background: #fafafa; }
  blockquote {
    border-left: 4px solid #ccc;
    margin: 16px 0;
    padding: 4px 16px;
    color: #555;
  }
  hr { border: none; border-top: 1px solid #ddd; margin: 32px 0; }
  a { color: #0366d6; }
</style>
"""

_MD_EXTENSIONS = ["tables", "fenced_code", "toc", "nl2br", "attr_list"]


def _convert(src: Path, out_dir: Path, prefix: str) -> Path:
    text = src.read_text(encoding="utf-8")
    body = markdown.markdown(text, extensions=_MD_EXTENSIONS)
    title = src.stem.replace("-", " ").replace("_", " ").title()
    html = (
        f"<!DOCTYPE html>\n"
        f"<html lang='en'>\n"
        f"<head>\n"
        f"  <meta charset='utf-8'>\n"
        f"  <meta name='viewport' content='width=device-width, initial-scale=1'>\n"
        f"  <title>{title}</title>\n"
        f"  {_CSS}\n"
        f"</head>\n"
        f"<body>\n{body}\n</body>\n"
        f"</html>\n"
    )
    out = out_dir / f"{prefix}{src.stem}.html"
    out.write_text(html, encoding="utf-8")
    return out


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("files", nargs=-1, type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--input-dir",
    "-d",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Convert all *.md files in this directory (sorted by name).",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(path_type=Path),
    help="Directory to write HTML files into. Created if absent. "
    "Default: 'html-export/' next to the first input file.",
)
@click.option("--prefix", "-p", default="", show_default=True, help="String prepended to every output filename.")
@click.option(
    "--open", "open_browser", is_flag=True, default=False, help="Open each generated HTML file in the default browser."
)
def main(files, input_dir, output_dir, prefix, open_browser):
    """Convert Markdown files to self-contained HTML.

    Accepts explicit FILE arguments, --input-dir, or both.
    """
    sources: list[Path] = list(files)

    if input_dir:
        sources += sorted(input_dir.glob("*.md"))

    if not sources:
        click.secho("No input files found. Pass markdown files as arguments or use --input-dir.", fg="yellow", err=True)
        raise SystemExit(1)

    # Resolve output directory
    if output_dir is None:
        output_dir = sources[0].parent / "html-export"
    output_dir.mkdir(parents=True, exist_ok=True)

    click.echo(f"Output directory: {output_dir}")

    for src in sources:
        out = _convert(src, output_dir, prefix)
        size_kb = out.stat().st_size / 1024
        click.secho(f"  ✓  {out.name}  ({size_kb:.1f} KB)", fg="green")
        if open_browser:
            webbrowser.open(out.resolve().as_uri())

    click.echo(f"\n{len(sources)} file(s) exported.")


if __name__ == "__main__":
    main()
