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

SITE_NAME = "福爾摩沙自閉大公社"
# 分類（順序即列表頁的區塊順序）→ 列表頁的錨點 id。改分類只改這裡。
CATEGORIES = {
    "行動記事": "action-notes",
    "社群公告": "announcements",
    "議題觀點": "perspectives",
    "技術教學": "tutorials",
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


def published(data: list[dict]) -> list[dict]:
    """排除草稿，依日期新到舊（同日依 slug 排序，結果可重現）。"""
    return sorted((a for a in data if not a.get("draft")), key=lambda a: (a["date"], a["slug"]), reverse=True)


def fmt_date(iso: str) -> str:
    y, m, d = iso.split("-")
    return f"{y} 年 {int(m)} 月 {int(d)} 日"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def author_name(a: dict) -> str:
    return a.get("author") or SITE_NAME


def article_url(slug: str) -> str:
    return f"{base()}/articles/{slug}.html"


def og_url(slug: str) -> str:
    return f"{base()}/assets/img/og/{slug}.jpg"


def og_alt(title: str) -> str:
    return f"{title}｜{SITE_NAME}的文章分享卡"


def shared_blocks() -> dict[str, str]:
    """從 index.html 複製閱讀設定、頁首、頁尾（去掉 aria-current），文章頁一律用這份，避免漂移。"""
    src = (ROOT / "index.html").read_text(encoding="utf-8")
    out = {}
    for key, pat in (("prefs", r'<section class="prefs".*?</section>'),
                     ("header", r'<header class="site-header">.*?</header>'),
                     ("footer", r'<footer class="site-footer">.*?</footer>')):
        m = re.search(pat, src, re.S)
        if not m:
            raise SystemExit(f"index.html 找不到共用區塊：{key}")
        out[key] = m.group(0).replace(' aria-current="page"', "")
    return out


def action_title(anchor: str) -> str | None:
    """actions.html 中某筆行動的標題（<li id> 內的 <h3>）。"""
    src = (ROOT / "actions.html").read_text(encoding="utf-8")
    m = re.search(rf'<li id="{re.escape(anchor)}">.*?<h3>(.*?)</h3>', src, re.S)
    return html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else None


def og_hash(a: dict) -> str:
    h = hashlib.sha256(json.dumps({"title": a["title"], "category": a["category"]}, ensure_ascii=False,
                                  sort_keys=True).encode())
    for f in OG_INPUT_FILES:
        h.update(f.read_bytes())
    return h.hexdigest()[:16]


def load_manifest() -> dict[str, str]:
    return json.loads(OG_MANIFEST.read_text(encoding="utf-8")) if OG_MANIFEST.exists() else {}


def save_manifest(m: dict[str, str]) -> None:
    OG_MANIFEST.write_text(json.dumps(dict(sorted(m.items())), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def robots_of(text: str) -> str:
    m = re.search(r'<meta name="robots" content="([^"]*)"', text)
    return m.group(1) if m else ""
