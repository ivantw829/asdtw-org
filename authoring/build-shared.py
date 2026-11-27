#!/usr/bin/env python3
"""把閱讀設定（含語言切換器）、頁首、頁尾從唯一來源 authoring/partials/<lang>/ 靜態寫進每一頁（不依賴 JS，報讀器讀到完整 HTML）。

  authoring/partials/<lang>/prefs.html    →  <!--shared:prefs--> … <!--/shared:prefs-->
  authoring/partials/<lang>/header.html   →  <!--shared:header--> … <!--/shared:header-->
  authoring/partials/<lang>/footer.html   →  <!--shared:footer--> … <!--/shared:footer-->

對象：根目錄所有 *.html、en/*.html、ja/*.html、articles/*.html 與譯文 en/articles/*.html、ja/articles/*.html。頁首的 aria-current="page" 由這支腳本加上：
只加在各語系的公開頁（404 與 noindex 頁除外）指向自己的導覽連結；片段檔本身不寫 aria-current。
改頁首／頁尾請改片段檔，不要改頁面裡標記之間的內容（會被覆寫，check.py 也會報錯）。
pre-commit 只在片段檔有變更時自動執行；會印出被改寫的檔案。
用法：python3 authoring/build-shared.py [--check]   （--check 只檢查是否最新，過期回傳 1）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402
import i18n as I  # noqa: E402

ROOT = L.ROOT


def pages() -> list[Path]:
    out = sorted(ROOT.glob("*.html"))
    for code in ("en", "ja"):
        d = ROOT / code
        if d.exists():
            out += sorted(d.glob("*.html"))
    if L.ARTICLES_DIR.exists():
        out += sorted(L.ARTICLES_DIR.glob("*.html"))
    for code in L.TRANSLATION_LOCALES:
        out += sorted((ROOT / code / "articles").glob("*.html"))
    return out


def self_href(rel: str, text: str) -> str | None:
    """各語系公開頁在導覽中的網址；其他頁（404、noindex、文章頁）沒有 aria-current。"""
    if rel == "404.html" or I.base_page(rel).startswith("articles/") or "noindex" in L.robots_of(text):
        return None
    loc = I.locale_of(rel)
    return I.page_href(loc, I.base_page(rel))


def header_for(locale: str, href: str | None) -> str:
    h = L.partial("header", locale)
    if href:
        link = f'<a href="{href}">'
        if link in h:
            h = h.replace(link, f'<a href="{href}" aria-current="page">', 1)
    return h


def prefs_for(locale: str, rel: str) -> str:
    p = L.partial("prefs", locale)
    return p.replace("<!--lang-links-->", I.render_lang_switch(rel))


def render() -> dict[Path, str]:
    out: dict[Path, str] = {}
    for p in pages():
        rel = p.relative_to(ROOT).as_posix()
        loc = I.locale_of(rel)
        t = p.read_text(encoding="utf-8")
        for key in L.SHARED_KEYS:
            if key == "header":
                inner = header_for(loc, self_href(rel, t))
            elif key == "prefs":
                inner = prefs_for(loc, rel)
            else:
                inner = L.partial(key, loc)
            t = L.replace_marked(t, f"<!--shared:{key}-->", f"<!--/shared:{key}-->", f"\n{inner}\n", rel)
        out[p] = t
    return out


def main() -> None:
    check = "--check" in sys.argv
    stale = []
    for p, new in render().items():
        if p.read_text(encoding="utf-8") != new:
            rel = p.relative_to(ROOT).as_posix()
            stale.append(rel)
            if not check:
                p.write_text(new, encoding="utf-8")
                print(rel)
    if check and stale:
        print("閱讀設定／頁首／頁尾與 authoring/partials/ 不一致：" + "、".join(stale)
              + "（共用區塊只改片段檔，再執行 python3 authoring/build-shared.py；直接改在頁面裡的內容會被覆寫）",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
