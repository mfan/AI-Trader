#!/usr/bin/env python3
"""
Render ML_STRATEGY_REPORT.md (or any markdown report) into a polished,
self-contained HTML page with a sticky table of contents.

Usage: .venv/bin/python tools/render_report.py [input.md] [output.html]
"""

import os
import re
import sys
import html
from datetime import datetime

import markdown

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CSS = """
:root {
  --bg: #0d1117; --panel: #161b22; --panel2: #1c2330; --border: #2d333f;
  --text: #e6edf3; --muted: #9da7b3; --accent: #4c9aff; --accent2: #7ee787;
  --red: #ff7b72; --green: #3fb950; --amber: #d29922; --code-bg: #0a0e14;
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.65; font-size: 16px;
}
.layout { display: flex; max-width: 1400px; margin: 0 auto; }
/* ─── Sidebar TOC ─── */
nav.toc {
  position: sticky; top: 0; align-self: flex-start; height: 100vh; overflow-y: auto;
  width: 280px; flex: 0 0 280px; padding: 32px 20px; border-right: 1px solid var(--border);
  background: var(--panel);
}
nav.toc .brand { font-size: 13px; letter-spacing: 2px; color: var(--accent); font-weight: 700; text-transform: uppercase; margin-bottom: 4px; }
nav.toc .subtitle { font-size: 12px; color: var(--muted); margin-bottom: 24px; }
nav.toc a { display: block; color: var(--muted); text-decoration: none; font-size: 13.5px; padding: 5px 10px; border-left: 2px solid transparent; border-radius: 0 6px 6px 0; }
nav.toc a:hover { color: var(--text); background: var(--panel2); }
nav.toc a.active { color: var(--accent); border-left-color: var(--accent); background: var(--panel2); }
nav.toc a.h3 { padding-left: 24px; font-size: 12.5px; }
/* ─── Main content ─── */
main { flex: 1; padding: 48px 56px 120px; max-width: 980px; }
h1 { font-size: 32px; margin: 0 0 8px; line-height: 1.25; }
h1 .sub { display: block; font-size: 15px; color: var(--muted); font-weight: 400; margin-top: 10px; }
h2 { font-size: 23px; margin: 48px 0 16px; padding-top: 16px; border-top: 1px solid var(--border); }
h2 .num { color: var(--accent); margin-right: 10px; }
h3 { font-size: 17.5px; margin: 32px 0 12px; color: var(--accent2); }
p { margin: 12px 0; }
a { color: var(--accent); }
strong { color: #fff; }
blockquote {
  margin: 20px 0; padding: 16px 20px; border-left: 3px solid var(--accent);
  background: var(--panel2); border-radius: 0 8px 8px 0; color: var(--text); font-style: italic;
}
code { background: var(--code-bg); padding: 2px 7px; border-radius: 5px; font-size: 13.5px; color: var(--accent2); font-family: "SF Mono", Menlo, Consolas, monospace; }
pre { background: var(--code-bg); padding: 18px 20px; border-radius: 10px; overflow-x: auto; border: 1px solid var(--border); }
pre code { background: none; padding: 0; color: #c9d1d9; font-size: 13px; line-height: 1.55; }
/* ─── Tables ─── */
table { border-collapse: collapse; width: 100%; margin: 20px 0; font-size: 14px; }
th { background: var(--panel2); text-align: left; padding: 10px 14px; border-bottom: 2px solid var(--accent); font-weight: 600; white-space: nowrap; }
td { padding: 9px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
tr:hover td { background: rgba(76,154,255,0.05); }
td:nth-child(n+2) { font-variant-numeric: tabular-nums; }
hr { border: none; border-top: 1px solid var(--border); margin: 40px 0; }
ul, ol { padding-left: 24px; }
li { margin: 5px 0; }
/* Verdict cell coloring */
td, p, li { --noop: 0; }
.verdict-pass { color: var(--green); font-weight: 700; }
.verdict-fail { color: var(--red); font-weight: 700; }
/* Meta header card */
.meta-card {
  display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px;
  margin: 28px 0 8px;
}
.meta-card .item { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }
.meta-card .label { font-size: 11px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); }
.meta-card .value { font-size: 14.5px; font-weight: 600; margin-top: 4px; }
.footer { margin-top: 64px; padding-top: 20px; border-top: 1px solid var(--border); color: var(--muted); font-size: 12.5px; }
@media (max-width: 960px) {
  nav.toc { display: none; }
  main { padding: 28px 20px 80px; }
}
"""

JS = """
// Scroll-spy for the TOC
const links = [...document.querySelectorAll('nav.toc a')];
const heads = links.map(a => document.getElementById(a.dataset.target)).filter(Boolean);
const spy = () => {
  let current = heads[0];
  for (const h of heads) if (h.getBoundingClientRect().top < 120) current = h;
  links.forEach(a => a.classList.toggle('active', a.dataset.target === (current && current.id)));
};
document.addEventListener('scroll', spy, { passive: true });
spy();
"""


def slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def render(md_path: str, out_path: str):
    with open(md_path) as f:
        md_text = f.read()

    # Split off the H1 title for a custom header
    title = "Strategy Report"
    m = re.match(r'^#\s+(.+)$', md_text, re.M)
    if m:
        title = m.group(1).strip()

    body_html = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists"],
    )

    # Build TOC from rendered headings + assign ids
    toc_entries = []

    def add_ids(match):
        level, inner = match.group(1), match.group(2)
        text = re.sub(r'<[^>]+>', '', inner).strip()
        sid = slugify(text)
        toc_entries.append((len(level), text, sid))
        return f'<h{level} id="{sid}">{inner}</h{level}>'

    body_html = re.sub(r'<h([23])>(.*?)</h\1>', add_ids, body_html, flags=re.S)

    # Number the H2s and decorate verdict emojis
    body_html = re.sub(r'(❌[^<]*)', r'<span class="verdict-fail">\1</span>', body_html)
    body_html = re.sub(r'(✅[^<]*)', r'<span class="verdict-pass">\1</span>', body_html)

    toc_html = "".join(
        f'<a href="#{sid}" data-target="{sid}" class="h{lvl}">{html.escape(text)}</a>'
        for lvl, text, sid in toc_entries
    )

    gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{CSS}</style>
</head>
<body>
<div class="layout">
<nav class="toc">
  <div class="brand">AI Trader</div>
  <div class="subtitle">Strategy Research Report</div>
  {toc_html}
</nav>
<main>
{body_html}
<div class="footer">Generated {gen_time} from <code>{html.escape(os.path.basename(md_path))}</code> · AI Trader — Jansen ML4T methodology</div>
</main>
</div>
<script>{JS}</script>
</body>
</html>"""

    with open(out_path, "w") as f:
        f.write(page)
    print(f"✅ Rendered {md_path} -> {out_path} ({len(page):,} bytes)")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(project_root, "ML_STRATEGY_REPORT.md")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(project_root, "docs", "strategy_report.html")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    render(src, dst)
