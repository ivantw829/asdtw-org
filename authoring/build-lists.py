#!/usr/bin/env python3
"""把文章列表靜態寫進 HTML（本站內容不依賴 JS）。改寫的區塊：

  articles.html   <!--lists:category-nav--> … <!--/lists:category-nav-->   分類跳轉（含篇數）
                  <!--lists:<分類 id>--> … <!--/lists:<分類 id>-->           各分類的文章，新到舊
  index.html      <!--lists:latest--> … <!--/lists:latest-->               最新三篇（首頁有這組標記才寫；上線前首頁沒有）
  articles/*.html <!--articlenav:start--> … <!--articlenav:end-->          上一篇／下一篇（草稿只有「回到文章列表」）

草稿（draft）不會出現在任何列表。md2article.py 與 pre-commit 會自動執行；會印出被改寫的檔案。
用法：python3 authoring/build-lists.py [--check]   （--check 只檢查是否最新，過期回傳 1）
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402

ROOT = L.ROOT
e = L.esc


def row(a: dict, with_category: bool = False) -> str:
    """列表項：與首頁「最近的行動」同樣式（標題連結＋灰字資訊），再加一段摘要。"""
    info = [f'<time datetime="{a["date"]}">{L.fmt_date(a["date"])}</time>', e(L.author_name(a)),
            f'閱讀約 {a["readingTime"]} 分鐘']
    if with_category:
        info.append(e(a["category"]))
    return (f'\n        <li><a href="/articles/{a["slug"]}.html">{e(a["title"])}</a><br>'
            f'<span class="muted">{"　".join(info)}</span>'
            f'\n          <p>{e(a["summary"])}</p></li>')


def category_nav(items: list[dict]) -> str:
    lis = "".join(f'\n        <li><a href="#{cid}">{e(name)}（{sum(a["category"] == name for a in items)} 篇）</a></li>'
                  for name, cid in L.CATEGORIES.items())
    return f'\n      <ul>{lis}\n      </ul>\n      '


def category_list(items: list[dict], name: str) -> str:
    rows = [a for a in items if a["category"] == name]
    if not rows:
        return '\n      <p class="muted">這個分類還沒有文章。</p>\n      '
    return '\n      <ul class="link-rows article-list">' + "".join(row(a) for a in rows) + "\n      </ul>\n      "


def latest(items: list[dict]) -> str:
    if not items:
        return '\n      <p class="muted">還沒有文章，敬請期待。</p>\n      '
    return '\n      <ul class="link-rows article-list">' + "".join(row(a, True) for a in items[:3]) + "\n      </ul>\n      "


def article_nav(a: dict, items: list[dict]) -> str:
    parts = []
    if not a.get("draft"):
        k = next(i for i, x in enumerate(items) if x["slug"] == a["slug"])
        newer = items[k - 1] if k > 0 else None
        older = items[k + 1] if k + 1 < len(items) else None
        if older:
            parts.append(f'<li class="article-nav-prev"><span class="muted">上一篇</span>'
                         f'<a href="/articles/{older["slug"]}.html">{e(older["title"])}</a></li>')
        if newer:
            parts.append(f'<li class="article-nav-next"><span class="muted">下一篇</span>'
                         f'<a href="/articles/{newer["slug"]}.html">{e(newer["title"])}</a></li>')
    parts.append('<li class="article-nav-all"><a href="/articles.html">回到文章列表</a></li>')
    return "\n      <ul>\n        " + "\n        ".join(parts) + "\n      </ul>\n    "


def replace(text: str, start: str, end: str, inner: str, where: str) -> str:
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        sys.exit(f"{where} 找不到標記 {start}")
    return pat.sub(lambda _: start + inner + end, text, count=1)


def render() -> dict[Path, str]:
    """回傳 {檔案: 應有的內容}（只含有列表區塊的檔案）。"""
    data = L.load_articles()
    items = L.published(data)
    out: dict[Path, str] = {}

    p = ROOT / "articles.html"
    if p.exists():
        t = p.read_text(encoding="utf-8")
        t = replace(t, "<!--lists:category-nav-->", "<!--/lists:category-nav-->", category_nav(items), p.name)
        for name, cid in L.CATEGORIES.items():
            t = replace(t, f"<!--lists:{cid}-->", f"<!--/lists:{cid}-->", category_list(items, name), p.name)
        out[p] = t

    p = ROOT / "index.html"
    t = p.read_text(encoding="utf-8")
    if "<!--lists:latest-->" in t:
        out[p] = replace(t, "<!--lists:latest-->", "<!--/lists:latest-->", latest(items), p.name)

    for a in data:
        p = L.ARTICLES_DIR / f"{a['slug']}.html"
        if p.exists():
            out[p] = replace(p.read_text(encoding="utf-8"), "<!--articlenav:start-->", "<!--articlenav:end-->",
                             article_nav(a, items), str(p.relative_to(ROOT)))
    return out


def main() -> None:
    check = "--check" in sys.argv
    stale = []
    for p, new in render().items():
        if p.read_text(encoding="utf-8") != new:
            rel = str(p.relative_to(ROOT))
            stale.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
                print(rel)
    if check and stale:
        print("文章列表的靜態內容過期：" + "、".join(stale) + "（請執行 python3 authoring/build-lists.py）", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
