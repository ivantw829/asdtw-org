#!/usr/bin/env python3
"""依 data/articles.json 產生 Atom 訂閱源 feed.xml（只用標準函式庫，移植自 me.asdtw.org）。

每篇放標題、摘要、分類、連結與全文（<content type="html">），讓閱讀器直接顯示整篇。排除草稿。
全文取自已產生的 articles/<slug>.html（導言＋正文＋參考資料），站內相對網址改成絕對網址。
只依 data/articles.json 與文章頁，沒有改內容就不會變，所以可重現（check.py 用 --check 比對）。
pre-commit 與 md2article.py 會自動執行。
用法：python3 authoring/build-feed.py [--check]
"""
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402

FEED = L.ROOT / "feed.xml"
TZ = "T00:00:00+08:00"  # 只有日期，沒有時間
PROSE_START = '<div class="prose">'
PROSE_END = "\n      </div>\n"  # article-template.html 中 prose 的結尾（內層元素縮排更深，不會撞到）
LEAD_RE = re.compile(r'<p class="lead">.*?</p>', re.S)
SOURCES_RE = re.compile(r'<aside class="article-sources"[^>]*>.*?</aside>', re.S)


def full_html(a: dict) -> str:
    """從文章頁取出導言、正文與參考資料，並把站內網址改成絕對網址（閱讀器多半不處理相對路徑）。"""
    path = L.ARTICLES_DIR / f"{a['slug']}.html"
    text = path.read_text(encoding="utf-8")
    i = text.find(PROSE_START)
    j = text.find(PROSE_END, i)
    if i < 0 or j < 0:
        sys.exit(f"✗ {path.relative_to(L.ROOT)} 找不到正文區塊（<div class=\"prose\">），無法產生訂閱源全文")
    lead = LEAD_RE.search(text, 0, i)
    parts = [lead.group(0) if lead else "", text[i + len(PROSE_START):j].strip()]
    m = SOURCES_RE.search(text, j)
    if m:
        parts.append(m.group(0))
    html = "\n".join(x for x in parts if x)
    b, url = L.base(), L.article_url(a["slug"])
    html = re.sub(r'(href|src)="/(?!/)', rf'\1="{b}/', html)
    return re.sub(r'href="#', f'href="{url}#', html)


def render() -> str:
    b = L.base()
    items = sorted(L.local_published(L.load_articles()),
                   key=lambda a: (a.get("updated") or a["date"], a["date"], a["slug"]), reverse=True)
    feed_updated = (items[0].get("updated") or items[0]["date"]) if items else "2026-07-31"  # 沒有文章時用社群建立日
    out = ['<?xml version="1.0" encoding="utf-8"?>',
           '<feed xmlns="http://www.w3.org/2005/Atom" xml:lang="zh-Hant-TW">',
           f"  <title>{escape(L.SITE_NAME)}｜文章</title>",
           f'  <link rel="alternate" type="text/html" href="{b}/articles.html"/>',
           f'  <link rel="self" type="application/atom+xml" href="{b}/feed.xml"/>',
           f"  <id>{b}/</id>",
           f"  <updated>{feed_updated}{TZ}</updated>",
           f"  <author><name>{escape(L.SITE_NAME)}</name><uri>{b}/</uri></author>"]
    for a in items:
        url = L.article_url(a["slug"])
        out += ["  <entry>",
                f"    <title>{escape(a['title'])}</title>",
                f'    <link rel="alternate" type="text/html" href="{url}"/>',
                f"    <id>{url}</id>",
                f"    <published>{a['date']}{TZ}</published>",
                f"    <updated>{a.get('updated') or a['date']}{TZ}</updated>",
                f"    <author><name>{escape(L.author_name(a))}</name></author>",
                f'    <summary type="text">{escape(a["summary"])}</summary>',
                f"    <content type=\"html\" xml:base={quoteattr(url)}>{escape(full_html(a))}</content>",
                f"    <category term={quoteattr(a['category'])}/>",
                "  </entry>"]
    out.append("</feed>")
    return "\n".join(out) + "\n"


def main() -> None:
    new = render()
    if "--check" in sys.argv:
        if not FEED.exists() or FEED.read_text(encoding="utf-8") != new:
            print("feed.xml 過期（請執行 python3 authoring/build-feed.py）", file=sys.stderr)
            sys.exit(1)
        return
    if not FEED.exists() or FEED.read_text(encoding="utf-8") != new:
        FEED.write_text(new, encoding="utf-8")
        print("feed.xml")


if __name__ == "__main__":
    main()
