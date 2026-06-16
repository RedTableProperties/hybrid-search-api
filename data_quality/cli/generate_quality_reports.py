#!/usr/bin/env python3
"""Build a local HTML quality report from Soda and GX JSON results."""

import json
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "great_expectations" / "uncommitted" / "data_docs" / "local_site"


def _load_json(path: Path):
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _render_section(title: str, rows: list[dict], name_key: str) -> str:
    if not rows:
        return f"<h2>{escape(title)}</h2><p>No results found.</p>"

    body = "".join(
        f"<tr><td>{escape(row.get(name_key, 'unknown'))}</td>"
        f"<td>{'pass' if row.get('success') else 'fail'}</td></tr>"
        for row in rows
    )
    return (
        f"<h2>{escape(title)}</h2>"
        "<table><thead><tr><th>Name</th><th>Status</th></tr></thead>"
        f"<tbody>{body}</tbody></table>"
    )


def main() -> int:
    soda = _load_json(ROOT / "soda_results.json") or []
    gx = _load_json(ROOT / "gx_results.json") or []

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Data Quality Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2937; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ color: #6b7280; margin-bottom: 2rem; }}
    table {{ border-collapse: collapse; width: 100%; max-width: 40rem; margin-bottom: 2rem; }}
    th, td {{ border: 1px solid #d1d5db; padding: 0.5rem 0.75rem; text-align: left; }}
    th {{ background: #f3f4f6; }}
  </style>
</head>
<body>
  <h1>Data Quality Report</h1>
  <p class="meta">Generated {escape(generated_at)}</p>
  {_render_section("Soda Checks", soda, "check")}
  {_render_section("Great Expectations Suites", gx, "suite")}
</body>
</html>
"""

    report_path = DOCS_DIR / "index.html"
    report_path.write_text(html, encoding="utf-8")
    print(f"Quality report written to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())