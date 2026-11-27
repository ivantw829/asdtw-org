#!/usr/bin/env python3
"""把文章列表靜態寫進 HTML（本站內容不依賴 JS）。改寫的區塊：

  [en/|ja/]articles.html  <!--lists:category-nav--> … <!--/lists:category-nav-->   分類跳轉（含篇數）
                          <!--lists:<分類 id>--> … <!--/lists:<分類 id>-->           各分類的文章，新到舊
  [en/|ja/]index.html     <!--lists:latest--> … <!--/lists:latest-->               最新三篇
  [en/|ja/]articles/*.html <!--articlenav:start--> … <!--articlenav:end-->         上一篇／下一篇（同語系之間；草稿只有「回到文章列表」）
                          <!--alternates:start--> … <!--alternates:end-->         原文與譯文互指的 hreflang（只有一種語系時留空）

草稿（draft）不會出現在任何列表。英／日文頁面：有該語系譯文的文章連到譯文並顯示譯文標題、摘要、標籤；
沒有譯文的維持原語言並加上 lang="zh-Hant-TW"。
md2article.py 與 pre-commit 會自動執行；會印出被改寫的檔案。
用法：python3 authoring/build-lists.py [--check]   （--check 只檢查是否最新，過期回傳 1）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402
import i18n as I  # noqa: E402

ROOT = L.ROOT
e = L.esc


def view(a: dict, locale: str) -> tuple[dict, bool]:
    """(要顯示的欄位, 是否為原文)：有該語系譯文就用譯文，否則用中文原文。"""
    if locale != "zh" and not L.is_external(a):
        tr = L.localized(a, locale)
        if tr:
            return tr, False
    return a, locale != "zh"


def author_html(a: dict, locale: str) -> str:
    if a.get("author"):
        name = e(a["author"])
        return name if locale == "zh" else f'<span lang="zh-Hant-TW">{name}</span>'
    return e(I.LOCALES[locale]["site_name"])


def title_link(a: dict, locale: str) -> str:
    """文章標題連結：站內文章連到 /articles/<slug>.html；跨站文章另開新視窗並附標示。"""
    a, foreign = view(a, locale)
    lang_attr = ' lang="zh-Hant-TW"' if foreign else ""
    if a.get("externalUrl"):
        href = e(a["externalUrl"])
        suffix = e(I.fmt_external_suffix(locale))
        if locale == "zh":
            return f'<a href="{href}" target="_blank" rel="noopener">{e(a["title"])}{suffix}</a>'
        return f'<a href="{href}" target="_blank" rel="noopener"><span lang="zh-Hant-TW">{e(a["title"])}</span>{suffix}</a>'
    href = "/" + L.article_rel(a["slug"], "zh" if foreign else locale)
    return f'<a href="{href}"{lang_attr}>{e(a["title"])}</a>'


def row(a: dict, locale: str = "zh", with_category: bool = False) -> str:
    """首頁「最新文章」的列表項：與「最近的行動」同樣式（標題連結＋灰字資訊），再加一段摘要。"""
    link = title_link(a, locale)
    a, foreign = view(a, locale)
    info = [
        f'<time datetime="{a["date"]}">{I.fmt_date(a["date"], locale)}</time>',
        author_html(a, locale),
        I.fmt_reading_time(a["readingTime"], locale),
    ]
    if with_category:
        info.append(e(I.LOCALES[locale]["categories"][a["category"]]))
    if a.get("externalSite"):
        info.append(e(a["externalSite"]))
    sep = " · " if locale == "en" else "　"
    lang_attr = ' lang="zh-Hant-TW"' if foreign else ""
    return (
        f'\n        <li>{link}<br>'
        f'<span class="muted">{sep.join(info)}</span>'
        f'\n          <p{lang_attr}>{e(a["summary"])}</p></li>'
    )


def card(a: dict, locale: str = "zh") -> str:
    """文章列表頁的卡片：標題（h3）、灰字資訊、摘要、標籤。
    資訊在 DOM 裡排在標題後面（報讀器先聽到標題），畫面上由 CSS 移到標題上方。"""
    link = title_link(a, locale)
    a, foreign = view(a, locale)
    meta_parts = [
        f'<time datetime="{a["date"]}">{I.fmt_date(a["date"], locale)}</time>',
        author_html(a, locale),
        I.fmt_reading_time(a["readingTime"], locale),
    ]
    if a.get("externalSite"):
        meta_parts.append(e(a["externalSite"]))
    info = '<span aria-hidden="true"> · </span>'.join(f"<span>{x}</span>" for x in meta_parts)
    lang_attr = ' lang="zh-Hant-TW"' if foreign else ""
    tags = ""
    if a.get("tags"):
        tags_label = I.LOCALES[locale]["tags_label"]
        tags = (
            f'\n          <p class="article-card-tags"><span class="visually-hidden">{tags_label}</span>'
            + "".join(f'<span class="tag tag-sub"{lang_attr}>{e(t)}</span>' for t in a["tags"])
            + "</p>"
        )
    return (
        f'\n        <li>'
        f'\n          <h3>{link}</h3>'
        f'\n          <p class="article-card-meta muted">{info}</p>'
        f'\n          <p{lang_attr}>{e(a["summary"])}</p>{tags}'
        f'\n        </li>'
    )


def category_nav(items: list[dict], locale: str = "zh") -> str:
    lis = "".join(
        f'\n        <li><a href="#{cid}">{e(I.fmt_cat_count(name, sum(a["category"] == name for a in items), locale))}</a></li>'
        for name, cid in L.CATEGORIES.items()
    )
    return f'\n      <ul>{lis}\n      </ul>\n      '


def category_list(items: list[dict], name: str, locale: str = "zh") -> str:
    rows = [a for a in items if a["category"] == name]
    if not rows:
        return f'\n      <p class="muted">{e(I.LOCALES[locale]["empty_category"])}</p>\n      '
    return '\n      <ul class="cards article-cards">' + "".join(card(a, locale) for a in rows) + "\n      </ul>\n      "


def latest(items: list[dict], locale: str = "zh") -> str:
    if not items:
        return f'\n      <p class="muted">{e(I.LOCALES[locale]["empty_latest"])}</p>\n      '
    return '\n      <ul class="link-rows article-list">' + "".join(row(a, locale, True) for a in items[:3]) + "\n      </ul>\n      "


def article_nav(a: dict, items: list[dict], locale: str = "zh") -> str:
    """上一篇／下一篇：items 是同語系有版本的已發布文章（新到舊），a 與 items 都是 localized() 後的欄位。"""
    s = I.LOCALES[locale]["article"]
    parts = []
    if not a.get("draft"):
        k = next(i for i, x in enumerate(items) if x["slug"] == a["slug"])
        newer = items[k - 1] if k > 0 else None
        older = items[k + 1] if k + 1 < len(items) else None
        if older:
            parts.append(f'<li class="article-nav-prev"><span class="muted">{s["prev"]}</span>'
                         f'<a href="/{L.article_rel(older["slug"], locale)}">{e(older["title"])}</a></li>')
        if newer:
            parts.append(f'<li class="article-nav-next"><span class="muted">{s["next"]}</span>'
                         f'<a href="/{L.article_rel(newer["slug"], locale)}">{e(newer["title"])}</a></li>')
    parts.append(f'<li class="article-nav-all"><a href="{I.page_href(locale, "articles.html")}">{s["all"]}</a></li>')
    return "\n      <ul>\n        " + "\n        ".join(parts) + "\n      </ul>\n    "


def alternates(a: dict) -> str:
    """原文與譯文互指的 hreflang；只有原文時留空。x-default 指向中文原文。"""
    locs = [c for c in I.LOCALE_ORDER if c == "zh" or c in L.translations(a)]
    if len(locs) < 2 or a.get("draft"):
        return ""
    lines = [f'<link rel="alternate" hreflang="{I.LOCALES[c]["html_lang"]}" href="{L.article_url(a["slug"], c)}">'
             for c in locs]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{L.article_url(a["slug"])}">')
    return "\n" + "\n".join(lines) + "\n"


replace = L.replace_marked


def render() -> dict[Path, str]:
    """回傳 {檔案: 應有的內容}（只含有列表區塊的檔案）。"""
    data = L.load_articles()
    items = L.published(data)
    out: dict[Path, str] = {}

    for locale in I.LOCALE_ORDER:
        prefix = I.LOCALES[locale]["prefix"].lstrip("/")
        base_dir = ROOT / prefix if prefix else ROOT

        p = base_dir / "articles.html"
        if p.exists():
            rel = p.relative_to(ROOT).as_posix()
            t = p.read_text(encoding="utf-8")
            t = replace(t, "<!--lists:category-nav-->", "<!--/lists:category-nav-->", category_nav(items, locale), rel)
            for name, cid in L.CATEGORIES.items():
                t = replace(t, f"<!--lists:{cid}-->", f"<!--/lists:{cid}-->", category_list(items, name, locale), rel)
            out[p] = t

        p = base_dir / "index.html"
        if p.exists():
            rel = p.relative_to(ROOT).as_posix()
            t = p.read_text(encoding="utf-8")
            if "<!--lists:latest-->" in t:
                out[p] = replace(t, "<!--lists:latest-->", "<!--/lists:latest-->", latest(items, locale), rel)

    local_items = L.local_published(data)
    for loc in I.LOCALE_ORDER:
        loc_items = [x for x in (L.localized(a, loc) for a in local_items) if x]
        for a in data:
            if L.is_external(a) or not L.localized(a, loc):
                continue
            p = L.article_path(a["slug"], loc)
            if p.exists():
                rel = p.relative_to(ROOT).as_posix()
                t = replace(p.read_text(encoding="utf-8"), "<!--articlenav:start-->", "<!--articlenav:end-->",
                            article_nav(L.localized(a, loc), loc_items, loc), rel)
                out[p] = replace(t, "<!--alternates:start-->", "<!--alternates:end-->", alternates(a), rel)
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
