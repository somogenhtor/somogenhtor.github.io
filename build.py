#!/usr/bin/env python3

import os
import re
import shutil
from datetime import datetime
from pathlib import Path

#pip install markdown
try:
    import markdown
    md = markdown.Markdown(extensions=["meta", "fenced_code", "tables", "toc"])
except ImportError:
    raise SystemExit("Run: pip install markdown")

POSTS_DIR = Path("posts")
OUT_DIR   = Path("docs")          # GitHub Pages can serve from /docs
SITE_NAME = "Somogenhtor"


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]", "-", name.lower()).strip("-")


def parse_post(path: Path) -> dict:
    """Parse a Markdown file; front-matter is key: value lines at the top."""
    raw = path.read_text(encoding="utf-8")
    meta, body = {}, raw

    # Simple front-matter: lines like `title: Foo` before a blank line
    lines = raw.splitlines()
    fm_lines, rest_start = [], 0
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            continue
        if line.strip() in ("---", "") and fm_lines:
            rest_start = i + 1
            break
        if ": " in line:
            fm_lines.append(line)
        else:
            break

    for line in fm_lines:
        k, _, v = line.partition(": ")
        meta[k.strip().lower()] = v.strip()

    body = "\n".join(lines[rest_start:]) if rest_start else raw

    md.reset()
    html_body = md.convert(body)

    # Fall back to filename-derived values
    stem = path.stem  # e.g. "2024-06-01-hello-world"
    date_match = re.match(r"(\d{4}-\d{2}-\d{2})", stem)
    date_str = meta.get("date") or (date_match.group(1) if date_match else "")

    title = meta.get("title") or stem.replace("-", " ").title()
    slug  = meta.get("slug")  or slugify(stem)

    return {
        "title":    title,
        "date":     date_str,
        "slug":     slug,
        "summary":  meta.get("summary", ""),
        "html":     html_body,
        "src_path": path,
    }


#HTML template

BASE_CSS = """
:root {
  --bg:      #fafaf8;
  --text:    #1c1c1c;
  --muted:   #888;
  --accent:  #2a5caa;
  --border:  #e2e2df;
  --max:     680px;
  --mono:    "JetBrains Mono", "Fira Code", monospace;
}

*, *::before, *::after { box-sizing: border-box; }

body {
  background: var(--bg);
  color: var(--text);
  font-family: Georgia, "Times New Roman", serif;
  font-size: 1.1rem;
  line-height: 1.75;
  margin: 0;
  padding: 2rem 1.25rem 4rem;
}

.wrap { max-width: var(--max); margin: 0 auto; }

/* ── Header ── */
header {
  border-bottom: 2px solid var(--text);
  padding-bottom: .75rem;
  margin-bottom: 2.5rem;
}
header a { text-decoration: none; color: inherit; }
header h1 { margin: 0; font-size: 1.4rem; font-family: system-ui, sans-serif; letter-spacing: -.02em; }
header p  { margin: .15rem 0 0; font-size: .85rem; color: var(--muted); font-family: system-ui, sans-serif; }

/* ── Post list (index) ── */
.post-list { list-style: none; padding: 0; margin: 0; }
.post-list li {
  display: flex;
  align-items: baseline;
  gap: 1.25rem;
  padding: .65rem 0;
  border-bottom: 1px solid var(--border);
}
.post-list time { font-size: .82rem; color: var(--muted); white-space: nowrap; font-family: system-ui, sans-serif; }
.post-list a { color: var(--accent); text-decoration: none; font-family: system-ui, sans-serif; }
.post-list a:hover { text-decoration: underline; }
.post-list .summary { font-size: .9rem; color: var(--muted); margin-top: .2rem; font-family: system-ui, sans-serif; }

/* ── Post page ── */
article h1 { font-size: 2rem; margin: 0 0 .3rem; line-height: 1.2; }
.post-meta  { font-size: .85rem; color: var(--muted); margin-bottom: 2.2rem; font-family: system-ui, sans-serif; }
article h2, article h3 { font-family: system-ui, sans-serif; }
article a   { color: var(--accent); }
article pre {
  background: #f0efe9;
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 1rem;
  overflow-x: auto;
  font-family: var(--mono);
  font-size: .88rem;
  line-height: 1.55;
}
article code { font-family: var(--mono); font-size: .9em; background: #f0efe9; padding: .1em .3em; border-radius: 3px; }
article pre code { background: none; padding: 0; }
article blockquote {
  margin: 1.5rem 0;
  padding: .75rem 1.25rem;
  border-left: 3px solid var(--accent);
  color: var(--muted);
}
article img { max-width: 100%; border-radius: 4px; }
article table { border-collapse: collapse; width: 100%; font-size: .95rem; }
article th, article td { border: 1px solid var(--border); padding: .45rem .75rem; text-align: left; }
article th { background: #f0efe9; }

.back { display: inline-block; margin-bottom: 2rem; font-family: system-ui, sans-serif; font-size: .9rem; color: var(--accent); text-decoration: none; }
.back:hover { text-decoration: underline; }

footer { margin-top: 3rem; font-size: .82rem; color: var(--muted); font-family: system-ui, sans-serif; }
"""


def page(title: str, body: str, is_post: bool = False) -> str:
    root = "../" if is_post else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — {SITE_NAME}</title>
  <style>{BASE_CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1><a href="{root}notes.html">{SITE_NAME}</a></h1>
  </header>
  {body}
</div>
</body>
</html>"""


#Builder

def build():
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir()
    (OUT_DIR / "posts").mkdir()

    # Copy any static assets (images, etc.) from posts/assets if present
    assets_src = POSTS_DIR / "assets"
    if assets_src.exists():
        shutil.copytree(assets_src, OUT_DIR / "assets")

    md_files = sorted(POSTS_DIR.glob("*.md"), reverse=True)
    posts = [parse_post(p) for p in md_files]

    # Individual post pages
    for post in posts:
        date_display = post["date"] or ""
        body = f"""
<a class="back" href="../notes.html">← All posts</a>
<article>
  <h1>{post['title']}</h1>
  <div class="post-meta">{date_display}</div>
  {post['html']}
</article>"""
        html = page(post["title"], body, is_post=True)
        (OUT_DIR / "posts" / f"{post['slug']}.html").write_text(html, encoding="utf-8")

    #Index page
    items = []
    for post in posts:
        summary = f'<div class="summary">{post["summary"]}</div>' if post["summary"] else ""
        items.append(f"""
  <li>
    <time>{post['date']}</time>
    <div>
      <a href="posts/{post['slug']}.html">{post['title']}</a>
      {summary}
    </div>
  </li>""")

    if items:
        list_html = f'<ul class="post-list">{"".join(items)}\n</ul>'
    else:
        list_html = "<p>No posts yet. Add a <code>.md</code> file to <code>posts/</code>.</p>"

    index_html = page(SITE_NAME, list_html)
    (OUT_DIR / "notes.html").write_text(index_html, encoding="utf-8")

    print(f"Built {len(posts)} post(s) → {OUT_DIR}/")


if __name__ == "__main__":
    build()
