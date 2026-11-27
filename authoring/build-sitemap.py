#!/usr/bin/env python3
"""依 CNAME、三語公開頁（根目錄、en/、ja/）、articles/*.html 與文章譯文（en/articles/、ja/articles/）產生 sitemap.xml（含 hreflang）。pre-commit 會自動執行。
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
for code in L.TRANSLATION_LOCALES:
    all_html += sorted(ROOT.glob(f"{code}/articles/*.html"))

pages = [
    p for p in all_html
    if p.name != "404.html" and "noindex" not in L.robots_of(p.read_text(encoding="utf-8"))
]


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def article_of(p: Path):
    """文章頁（原文或譯文）→ (localized 欄位, 語系)；不是文章頁回傳 None。"""
    r = rel(p)
    if not I.base_page(r).startswith("articles/") or p.stem not in articles:
        return None
    loc = I.locale_of(r)
    a = L.localized(articles[p.stem], loc)
    return (a, loc) if a else None


def lastmod(p: Path) -> str:
    art = article_of(p)
    if art:
        return art[0].get("updated") or art[0]["date"]
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
    is_art = I.base_page(r).startswith("articles/")
    loc_idx = I.LOCALE_ORDER.index(I.locale_of(r))
    bp = I.base_page(r)
    return (is_art, loc_idx, bp != "index.html", r) if not is_art else (is_art, 0, False, f"{p.stem}/{loc_idx}")


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
    elif article_of(p):
        a = articles[p.stem]
        locs = [c for c in I.LOCALE_ORDER if c == I.DEFAULT_LOCALE or c in L.translations(a)]
        if len(locs) > 1:
            for code in locs:
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{I.LOCALES[code]["html_lang"]}" href="{L.article_url(a["slug"], code)}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{L.article_url(a["slug"])}"/>')
    lines.append("  </url>")
lines.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(order)} 頁")
