#!/usr/bin/env python3
"""依 CNAME、根目錄 HTML 與 articles/*.html 產生 sitemap.xml。pre-commit 會自動執行。
不收錄：404、robots 為 noindex 的頁面（上線前的文章列表、草稿文章）。
文章的 lastmod 用 data/articles.json 的 updated 或 date；其他頁用 git 最後修改日。"""
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402

ROOT = L.ROOT
domain = L.domain()
articles = {a["slug"]: a for a in L.load_articles()}
pages = [p for p in sorted(ROOT.glob("*.html")) + sorted(ROOT.glob("articles/*.html"))
         if p.name != "404.html" and "noindex" not in L.robots_of(p.read_text(encoding="utf-8"))]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def lastmod(p: Path) -> str:
    if p.parent == L.ARTICLES_DIR and p.stem in articles:
        a = articles[p.stem]
        return a.get("updated") or a["date"]
    try:
        out = subprocess.run(["git", "log", "-1", "--format=%cs", "--", rel(p)],
                             cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return date.today().isoformat()


def loc(p: Path) -> str:
    return f"https://{domain}/" if rel(p) == "index.html" else f"https://{domain}/{rel(p)}"


order = sorted(pages, key=lambda p: (rel(p) != "index.html", "/" in rel(p), rel(p)))
lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p in order:
    lines += ["  <url>", f"    <loc>{loc(p)}</loc>", f"    <lastmod>{lastmod(p)}</lastmod>", "  </url>"]
lines.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(order)} 頁")
