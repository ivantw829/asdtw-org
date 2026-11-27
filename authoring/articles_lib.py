"""文章欄位的共用定義。md2article／build-lists／build-feed／build-og／build-sitemap／check 都從這裡讀，
分類、日期格式、共用區塊與分享圖雜湊只有這一份，不必在各腳本之間手動同步。"""
import hashlib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "articles.json"
ARTICLES_DIR = ROOT / "articles"
OG_DIR = ROOT / "assets" / "img" / "og"
OG_MANIFEST = ROOT / "authoring" / "og" / "manifest.json"  # 每張文章分享圖「上次產生時的輸入」雜湊
OG_CARD = ROOT / "authoring" / "og" / "article-card.html"
OG_INPUT_FILES = (OG_CARD, ROOT / "assets" / "img" / "brand" / "lockup-dark.svg")
# 譯文分享圖另用一份範本（含「文章」字樣與字體的語系切換），改它不會讓中文原文的分享圖過期
OG_CARD_I18N = ROOT / "authoring" / "og" / "article-card-i18n.html"
OG_INPUT_FILES_I18N = (OG_CARD_I18N, ROOT / "assets" / "img" / "brand" / "lockup-dark.svg")
DEFAULT_LOCALE = "zh"
TRANSLATION_LOCALES = ("en", "ja")  # 文章譯文：en/articles/<slug>.html、ja/articles/<slug>.html
TRANSLATION_KEYS = ("title", "summary", "tags", "readingTime", "updated")  # translations.<語系> 可有的欄位

SITE_NAME = "福爾摩沙自閉大公社"
# 分類（順序即列表頁的區塊順序）→ 列表頁的錨點 id。改分類只改這裡。
CATEGORIES = {
    "社群公告": "announcements",
    "議題觀點": "perspectives",
    "技術教學": "tutorials",
    "行動記事": "action-notes",
}
SLUG_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def domain() -> str:
    return (ROOT / "CNAME").read_text(encoding="utf-8").strip()


def base() -> str:
    return f"https://{domain()}"


def load_articles() -> list[dict]:
    if not DATA.exists():
        return []
    return json.loads(DATA.read_text(encoding="utf-8"))


def save_articles(data: list[dict]) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def is_external(a: dict) -> bool:
    """是否為指向其他網站的跨站文章連結（本站不存全文頁）。"""
    return bool(a.get("externalUrl"))


def published(data: list[dict]) -> list[dict]:
    """排除草稿，依日期新到舊（同日依 slug 排序，結果可重現）。"""
    return sorted((a for a in data if not a.get("draft")), key=lambda a: (a["date"], a["slug"]), reverse=True)


def local_published(data: list[dict]) -> list[dict]:
    """排除草稿與跨站連結，僅保留本站有全文的文章。"""
    return [a for a in published(data) if not is_external(a)]


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{y} 年 {int(m)} 月 {int(d)} 日"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def site_name(locale: str = DEFAULT_LOCALE) -> str:
    import i18n
    return i18n.LOCALES[locale]["site_name"]


def author_name(a: dict, locale: str = DEFAULT_LOCALE) -> str:
    return a.get("author") or site_name(locale)


def translations(a: dict) -> dict[str, dict]:
    """文章已有的譯文 {語系: 欄位}（不含中文原文）。"""
    return {k: v for k, v in (a.get("translations") or {}).items() if k in TRANSLATION_LOCALES}


def localized(a: dict, locale: str = DEFAULT_LOCALE) -> dict | None:
    """某語系版本的文章欄位：中文回傳原資料；譯文以 translations.<語系> 覆蓋標題、摘要、標籤、閱讀時間、更新日，
    日期、分類、作者、行動沿用原文。沒有該語系譯文回傳 None。"""
    if locale == DEFAULT_LOCALE:
        return a
    tr = translations(a).get(locale)
    if not tr:
        return None
    out = {k: v for k, v in a.items() if k not in ("translations", "updated")}
    out.update(tr)
    return out


def article_rel(slug: str, locale: str = DEFAULT_LOCALE) -> str:
    """文章頁的相對路徑：articles/<slug>.html、en/articles/<slug>.html…"""
    return f"articles/{slug}.html" if locale == DEFAULT_LOCALE else f"{locale}/articles/{slug}.html"


def article_path(slug: str, locale: str = DEFAULT_LOCALE) -> Path:
    return ROOT / article_rel(slug, locale)


def article_url(slug: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{base()}/{article_rel(slug, locale)}"


def og_key(slug: str, locale: str = DEFAULT_LOCALE) -> str:
    """分享圖在 manifest 的鍵，也是 assets/img/og/ 之下不含副檔名的路徑。"""
    return slug if locale == DEFAULT_LOCALE else f"{locale}/{slug}"


def og_file(slug: str, locale: str = DEFAULT_LOCALE) -> Path:
    return OG_DIR / f"{og_key(slug, locale)}.jpg"


def og_url(slug: str, locale: str = DEFAULT_LOCALE) -> str:
    return f"{base()}/assets/img/og/{og_key(slug, locale)}.jpg"


def og_alt(title: str, locale: str = DEFAULT_LOCALE) -> str:
    if locale == "en":
        return f"{title} | Article share card from {site_name(locale)}"
    if locale == "ja":
        return f"{title}｜{site_name(locale)}の記事シェアカード"
    return f"{title}｜{SITE_NAME}的文章分享卡"


def page_title(title: str, locale: str = DEFAULT_LOCALE) -> str:
    """<title>：文章標題＋站名（英文用半形直線，與英文版其他頁面一致）。"""
    sep = " | " if locale == "en" else "｜"
    return f"{title}{sep}{site_name(locale)}"


PARTIALS_DIR = ROOT / "authoring" / "partials"
SHARED_KEYS = ("prefs", "header", "footer")  # 閱讀設定、頁首、頁尾；唯一來源是 authoring/partials/<lang>/<key>.html


def partial(key: str, locale: str = "zh") -> str:
    """片段檔內容（不含標記、不含 aria-current）。"""
    p = PARTIALS_DIR / locale / f"{key}.html"
    if not p.exists():
        raise SystemExit(f"找不到共用區塊的片段檔：{p.relative_to(ROOT)}")
    return p.read_text(encoding="utf-8").strip("\n")


def wrap_shared(key: str, inner: str) -> str:
    return f"<!--shared:{key}-->\n{inner}\n<!--/shared:{key}-->"


def shared_blocks(rel: str = "articles/placeholder.html") -> dict[str, str]:
    """閱讀設定、頁首、頁尾（連同 <!--shared:…--> 標記、沒有 aria-current）。文章頁產生時用這份，
    之後由 build-shared.py 跟其他頁面一起維護。"""
    import i18n
    loc = i18n.locale_of(rel)
    blocks = {}
    for k in SHARED_KEYS:
        inner = partial(k, loc)
        if k == "prefs":
            inner = inner.replace("<!--lang-links-->", i18n.render_lang_switch(rel))
        blocks[k] = wrap_shared(k, inner)
    return blocks


def replace_marked(text: str, start: str, end: str, inner: str, where: str) -> str:
    """把 start 與 end 標記之間的內容換成 inner；找不到標記就結束程式並說明是哪個檔案。"""
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        raise SystemExit(f"{where} 找不到標記 {start} … {end}")
    return pat.sub(lambda _: start + inner + end, text, count=1)


def action_title(anchor: str, locale: str = DEFAULT_LOCALE) -> str | None:
    """[en/|ja/]actions.html 中某筆行動的標題（<li id> 內的 <h3>；三語的 id 相同）。"""
    src = (ROOT / ("actions.html" if locale == DEFAULT_LOCALE else f"{locale}/actions.html")).read_text(encoding="utf-8")
    m = re.search(rf'<li id="{re.escape(anchor)}">.*?<h3>(.*?)</h3>', src, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def og_hash(a: dict, locale: str = DEFAULT_LOCALE) -> str:
    """分享圖的輸入雜湊。a 是 localized() 之後的欄位。中文原文的算法維持不變（不讓既有分享圖過期）。"""
    key = {"title": a["title"], "category": a["category"]}
    files = OG_INPUT_FILES
    if locale != DEFAULT_LOCALE:
        key["locale"] = locale
        files = OG_INPUT_FILES_I18N
    h = hashlib.sha256(json.dumps(key, ensure_ascii=False, sort_keys=True).encode())
    for f in files:
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def load_manifest() -> dict[str, str]:
    return json.loads(OG_MANIFEST.read_text(encoding="utf-8")) if OG_MANIFEST.exists() else {}


def save_manifest(m: dict[str, str]) -> None:
    OG_MANIFEST.write_text(json.dumps(dict(sorted(m.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def robots_of(text: str) -> str:
    m = re.search(r'<meta name="robots" content="([^"]*)"', text)
    return m.group(1) if m else ""
