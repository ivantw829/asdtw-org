#!/usr/bin/env python3
"""依 data/articles.json 產生 Atom 訂閱源 feed.xml（只用標準函式庫，移植自 me.asdtw.org）。

只放標題、摘要、分類與連結，讀者點進網站讀全文。排除草稿。
日期取自文章資料，沒有改內容就不會變，所以可重現（check.py 用 --check 比對）。
pre-commit 與 md2article.py 會自動執行。
用法：python3 authoring/build-feed.py [--check]
"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402

FEED = L.ROOT / "feed.xml"
TZ = "T00:00:00+08:00"  # 只有日期，沒有時間


def render() -> str:
    b = L.base()
    items = sorted(L.published(L.load_articles()),
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
