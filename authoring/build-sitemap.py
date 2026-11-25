#!/usr/bin/env python3
"""依 CNAME、三語公開頁（根目錄、en/、ja/）與 articles/*.html 產生 sitemap.xml（含 hreflang）。pre-commit 會自動執行。
不收錄：404、robots 為 noindex 的頁面（上線前的文章列表、草稿文章）。
文章的 lastmod 用 data/articles.json 的 updated 或 date；其他頁用 git 最後修改日。"""
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402
import i18n as I  # noqa: E402

ROOT = L.ROOT
base = L.base()
articles = {a["slug"]: a for a in L.load_articles()}

all_html = sorted(ROOT.glob("*.html"))
for code in ("en", "ja"):
    if (ROOT / code).exists():
        all_html += sorted((ROOT / code).glob("*.html"))
all_html += sorted(ROOT.glob("articles/*.html"))

pages = [
    p for p in all_html
    if p.name != "404.html" and "noindex" not in L.robots_of(p.read_text(encoding="utf-8"))
]


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
    return I.canonical_url(base, rel(p))


def sort_key(p: Path):
    r = rel(p)
    is_art = r.startswith("articles/")
    loc_idx = I.LOCALE_ORDER.index(I.locale_of(r)) if not is_art else 99
    bp = I.base_page(r)
    return (is_art, loc_idx, bp != "index.html", r)


order = sorted(pages, key=sort_key)
lines = [
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">',
]
for p in order:
    r = rel(p)
    lines += ["  <url>", f"    <loc>{loc(p)}</loc>", f"    <lastmod>{lastmod(p)}</lastmod>"]
    if I.is_localized_public(r):
        bp = I.base_page(r)
        for code in I.LOCALE_ORDER:
            hreflang = I.LOCALES[code]["html_lang"]
            href = I.page_url(base, code, bp)
            lines.append(f'    <xhtml:link rel="alternate" hreflang="{hreflang}" href="{href}"/>')
        lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{I.page_url(base, I.DEFAULT_LOCALE, bp)}"/>')
    lines.append("  </url>")
lines.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(order)} 頁")
