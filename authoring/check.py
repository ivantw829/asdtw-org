#!/usr/bin/env python3
"""網站品質與無障礙檢查。CI 與 pre-commit 都會執行；任何問題都會列出後以非 0 結束。

檢查：頁面結構與地標、標題層級、跳過連結、外部資源、連結與錨點、導覽／頁尾一致、
meta 一致、sitemap、CSS 色票對比（WCAG 相對亮度）、字級單位、文章（資料、分享圖、列表、訂閱源）。
"""
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "authoring"))
import articles_lib as AL  # noqa: E402
errors: list[str] = []


def err(where: str, msg: str) -> None:
    errors.append(f"{where}: {msg}")


# ---------------------------------------------------------------- HTML 解析
class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags: list[tuple[str, dict]] = []
        self.headings: list[int] = []
        self.ids: list[str] = []
        self.links: list[dict] = []
        self.metas: dict[str, str] = {}
        self.canonical = ""
        self.title = ""
        self._in_title = False
        self._cur_a: dict | None = None
        self.regions: dict[str, list[str]] = {"header": [], "footer": [], "prefs": []}
        self._stack: list[str] = []
        self.lang = ""
        self.first_focusable: dict | None = None
        self.ldjson: list[str] = []
        self._in_ld = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag == "html":
            self.lang = a.get("lang", "")
        if tag == "title":
            self._in_title = True
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld = True
            self.ldjson.append("")
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.headings.append(int(tag[1]))
        if "id" in a:
            self.ids.append(a["id"])
        if tag == "meta":
            key = a.get("name") or a.get("property")
            if key:
                self.metas[key] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href", "")
        if tag == "a":
            self._cur_a = {"attrs": a, "text": ""}
            if self.first_focusable is None:
                self.first_focusable = a
        if tag == "button" and self.first_focusable is None:
            self.first_focusable = a
        # 區塊內容擷取（用於比對各頁是否一致）
        if tag in ("header", "footer"):
            self._stack.append(tag)
        if tag == "section" and "data-prefs" in a:
            self._stack.append("prefs")
        for r in self._stack[-1:]:
            self.regions[r].append(self._fmt(tag, a))

    @staticmethod
    def _fmt(tag, a):
        a = {k: v for k, v in a.items() if k != "aria-current"}
        return "<" + tag + "".join(f' {k}="{v}"' for k, v in sorted(a.items())) + ">"

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script":
            self._in_ld = False
        if tag == "a" and self._cur_a is not None:
            self.links.append(self._cur_a)
            self._cur_a = None
        if self._stack and ((tag in ("header", "footer") and self._stack[-1] == tag) or (tag == "section" and self._stack[-1] == "prefs")):
            self._stack.pop()

    def handle_data(self, data):
        if self._in_ld:
            self.ldjson[-1] += data
            return
        if self._in_title:
            self.title += data
        if self._cur_a is not None:
            self._cur_a["text"] += data
        if self._stack and data.strip():
            self.regions[self._stack[-1]].append(data.strip())


def load(p: Path) -> Page:
    pg = Page()
    pg.feed(p.read_text(encoding="utf-8"))
    return pg


domain = (ROOT / "CNAME").read_text().strip()
html_files = sorted(ROOT.glob("*.html")) + sorted(ROOT.glob("articles/*.html"))
pages = {p.relative_to(ROOT).as_posix(): load(p) for p in html_files}
# 公開頁：404 以外、沒有 noindex 的頁面（未公開的文章列表與草稿文章是 noindex）
public = [n for n in pages if n != "404.html" and "noindex" not in pages[n].metas.get("robots", "")]
root_public = [n for n in public if "/" not in n]


def jpeg_size(path: Path) -> tuple[int, int] | None:
    """讀 JPEG 標頭取得 (寬, 高)，不依賴任何套件。"""
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i + 9 < len(data):
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xC0, 0xC1, 0xC2):
            return int.from_bytes(data[i + 7:i + 9], "big"), int.from_bytes(data[i + 5:i + 7], "big")
        i += 2 + int.from_bytes(data[i + 2:i + 4], "big")
    return None


def seo_checks(name: str, pg: Page) -> None:
    m = pg.metas
    base = f"https://{domain}"
    # 搜尋引擎
    robots = m.get("robots", "")
    if name == "404.html":
        if "noindex" not in robots:
            err(name, '404 必須有 <meta name="robots" content="noindex">')
    elif robots.startswith("noindex"):
        if not (name == "articles.html" or name.startswith("articles/")):
            err(name, "只有文章列表（上線前）與草稿文章可以是 noindex")
    elif not robots.startswith("index,follow"):
        err(name, '缺少 <meta name="robots" content="index,follow,…">')
    desc = m.get("description", "")
    if name != "404.html" and not 50 <= len(desc) <= 160:
        err(name, f"description 長度應為 50～160 字（目前 {len(desc)} 字）")
    # 社群分享
    img = f"{base}/assets/img/og.jpg"
    if name.startswith("articles/"):
        img = AL.og_url(Path(name).stem)  # 文章各自的分享圖，第 9 節檢查檔案
    for key in ("og:image", "twitter:image"):
        if m.get(key) != img:
            err(name, f"{key} 必須是 {img}")
    if m.get("twitter:card") != "summary_large_image":
        err(name, 'twitter:card 必須是 "summary_large_image"')
    if m.get("og:image:width") != "1200" or m.get("og:image:height") != "630":
        err(name, "og:image:width／height 必須是 1200／630")
    if not m.get("og:image:alt") or m.get("og:image:alt") != m.get("twitter:image:alt"):
        err(name, "og:image:alt 與 twitter:image:alt 必須存在且一致")
    # 圖示
    rels = [(a.get("rel"), a.get("href")) for x, a in pg.tags if x == "link" and a.get("rel") in ("icon", "apple-touch-icon")]
    for need in ("icon", "apple-touch-icon"):
        if not any(r == need for r, _ in rels):
            err(name, f"缺少 <link rel=\"{need}\">")
    for _, href in rels:
        if not href or not href.startswith("/") or not (ROOT / href.lstrip("/")).exists():
            err(name, f"圖示檔案不存在：{href}")
    # JSON-LD
    if name == "404.html":
        return
    if not pg.ldjson:
        err(name, "缺少 JSON-LD（<script type=\"application/ld+json\">）")
        return
    for raw in pg.ldjson:
        try:
            data = json.loads(raw)
        except ValueError as e:
            err(name, f"JSON-LD 不是合法 JSON：{e}")
            continue
        nodes = data.get("@graph", [data])
        types = {n.get("@type") for n in nodes}
        if name == "index.html":
            if not {"Organization", "WebSite"} <= types:
                err(name, "首頁 JSON-LD 需要 Organization 與 WebSite")
        elif "BreadcrumbList" not in types:
            err(name, "內頁 JSON-LD 需要 BreadcrumbList")
        else:
            crumbs = next(n for n in nodes if n.get("@type") == "BreadcrumbList")
            last = crumbs["itemListElement"][-1]["item"]
            if last != pg.canonical:
                err(name, f"BreadcrumbList 最後一項 {last} 與 canonical 不一致")
        blob = json.dumps(data, ensure_ascii=False)
        for bad in ("捍衛全台學權行動", "ouob@"):
            if bad in blob:
                err(name, f"JSON-LD 不得出現：{bad}")


# ---------------------------------------------------------------- 1. 各頁檢查
for name, pg in pages.items():
    raw = (ROOT / name).read_text(encoding="utf-8")
    tags = pg.tags

    if "捍衛全台學權行動" in raw:
        err(name, "網站上不得出現「捍衛全台學權行動」（內容守則）")

    def count(t):
        return sum(1 for x, _ in tags if x == t)

    if pg.lang != "zh-Hant-TW":
        err(name, f'<html lang> 必須是 "zh-Hant-TW"（目前：{pg.lang!r}）')
    if not pg.title.strip():
        err(name, "缺少 <title>")
    if not pg.metas.get("description"):
        err(name, "缺少 meta description")
    viewport = pg.metas.get("viewport", "")
    if "user-scalable=no" in viewport.replace(" ", "") or "maximum-scale" in viewport:
        err(name, "viewport 不得禁止縮放（user-scalable=no／maximum-scale）")
    if count("h1") != 1:
        err(name, f"必須恰好一個 <h1>（目前 {count('h1')} 個）")
    # 標題不跳級
    prev = 0
    for h in pg.headings:
        if prev and h > prev + 1:
            err(name, f"標題跳級：h{prev} 之後直接 h{h}")
        prev = h
    if count("main") != 1:
        err(name, "必須恰好一個 <main>")
    for t in ("header", "nav", "footer"):
        if count(t) < 1:
            err(name, f"缺少 <{t}> 地標")
    for t in ("nav",):
        for x, a in tags:
            if x == t and not a.get("aria-label"):
                err(name, "<nav> 需要 aria-label")
    # 跳到主要內容：第一個可聚焦元素
    ff = pg.first_focusable or {}
    if ff.get("href") != "#main" or "skip-link" not in ff.get("class", ""):
        err(name, '第一個可聚焦元素必須是 class="skip-link"、href="#main" 的連結')
    mains = [a for x, a in tags if x == "main"]
    if mains and (mains[0].get("id") != "main" or mains[0].get("tabindex") != "-1"):
        err(name, '<main> 需要 id="main" 與 tabindex="-1"')
    # 禁止事項
    if "{{" in raw or "}}" in raw:
        err(name, "殘留 {{ }} 占位符")
    if re.search(r"\sstyle\s*=", raw) or "<style" in raw:
        err(name, "不得使用 style= 或 <style>，樣式一律放 assets/css/style.css")
    if re.search(r"\son[a-z]+\s*=", raw):
        err(name, "不得使用行內事件屬性（onclick 等）")
    scripts = [a for x, a in tags if x == "script"]
    for s in scripts:
        if s.get("type") == "application/ld+json" and "src" not in s:
            continue
        if s.get("src") != "/assets/js/prefs.js":
            err(name, f"只允許載入 /assets/js/prefs.js 與 JSON-LD（發現：{s}）")
    if "<script>" in raw:
        err(name, "不得有行內 <script>")
    for x, a in tags:
        if x == "link" and a.get("rel") == "stylesheet" and a.get("href") != "/assets/css/style.css":
            err(name, f"不得載入外部或額外的 CSS：{a.get('href')}")
        if x in ("img",):
            if not a.get("alt", "").strip():
                err(name, "<img> 必須有非空的 alt（裝飾圖請改用 CSS 背景圖並 aria-hidden）")
            if not (a.get("width") and a.get("height")):
                err(name, "<img> 必須指定 width 與 height（避免版面位移）")
        if x in ("iframe", "video", "audio", "embed", "object"):
            err(name, f"<{x}> 尚未有無障礙規範，請先更新 check.py 與無障礙聲明再加入")
        if x == "button" and a.get("type") != "button":
            err(name, '<button> 必須指定 type="button"')
        if x == "meta" and a.get("name") == "viewport":
            pass
    # id 不重複
    dup = {i for i in pg.ids if pg.ids.count(i) > 1}
    if dup:
        err(name, f"id 重複：{sorted(dup)}")
    # meta 一致
    if name != "404.html":
        if pg.canonical != pg.metas.get("og:url"):
            err(name, "canonical 與 og:url 不一致")
        expect = f"https://{domain}/" if name == "index.html" else f"https://{domain}/{name}"
        if pg.canonical != expect:
            err(name, f"canonical 應為 {expect}（目前 {pg.canonical}）")
    if pg.metas.get("og:title") != pg.title.strip() or pg.metas.get("twitter:title") != pg.title.strip():
        err(name, "title、og:title、twitter:title 必須逐字一致")
    d = pg.metas.get("description")
    if d != pg.metas.get("og:description") or d != pg.metas.get("twitter:description"):
        err(name, "description、og:description、twitter:description 必須逐字一致")
    seo_checks(name, pg)
    if raw.count("<img") != raw.count("<figcaption"):
        err(name, "每張 <img> 都要放在 <figure> 並附 <figcaption>")
    # 切頁轉場：需要 rel=expect 與 #page-end，否則切換瞬間會閃空白
    if name != "404.html":
        has_expect = any(x == "link" and a.get("rel") == "expect" and a.get("href") == "#page-end" and "blocking" in a for x, a in tags)
        if not has_expect:
            err(name, '缺少 <link rel="expect" href="#page-end" blocking="render">（切頁轉場需要）')
        if "page-end" not in pg.ids:
            err(name, '缺少結尾的 <span id="page-end" hidden></span>（切頁轉場需要）')
    # 連結
    for lk in pg.links:
        a, text = lk["attrs"], lk["text"].strip()
        href = a.get("href", "")
        if not href:
            err(name, "有 <a> 沒有 href")
            continue
        if not text and not a.get("aria-label"):
            err(name, f"連結沒有可讀文字：{href}")
        if re.fullmatch(r"(點(此|我|這裡)|這裡|here|click here|更多|more)", text, re.I):
            err(name, f"連結文字不明確：「{text}」（{href}）")
        if href.startswith(("http://", "https://")):
            if href.startswith("http://"):
                err(name, f"外部連結請用 https：{href}")
            if a.get("target") == "_blank":
                if "noopener" not in a.get("rel", ""):
                    err(name, f"target=_blank 必須加 rel=noopener：{href}")
                if "另開新視窗" not in text:
                    err(name, f"另開新視窗的連結文字須註明「另開新視窗」：{text}")
            elif f"//{domain}" not in href:
                err(name, f"外部連結必須 target=_blank rel=noopener：{href}")
        elif href.startswith("mailto:"):
            pass
        else:
            if "另開新視窗" in text:
                err(name, f"站內連結不應標示「另開新視窗」：{href}")
            if a.get("target") == "_blank":
                err(name, f"站內連結不應另開新視窗：{href}")
            path, _, frag = href.partition("#")
            target_name = name if path == "" else ("index.html" if path == "/" else path.lstrip("/"))
            if not path.startswith("/") and path != "":
                err(name, f"站內連結請用 / 開頭的絕對路徑：{href}")
            elif target_name not in pages and not (not frag and (ROOT / target_name).is_file()):
                err(name, f"站內連結指向不存在的頁面：{href}")
            elif frag and frag not in pages[target_name].ids:
                err(name, f"站內錨點不存在：{href}")

# ---------------------------------------------------------------- 2. 共用區塊一致
ref_name = "index.html"
for region in ("header", "footer", "prefs"):
    ref = pages[ref_name].regions[region]
    for name in pages:
        if name != ref_name and pages[name].regions[region] != ref:
            err(name, f"{region} 區塊與 index.html 不一致（共用區塊必須逐字相同；header 只允許 aria-current 不同）")

# 導覽：根目錄的公開頁恰好一個 aria-current，且指向自己；文章頁與未公開頁沒有
for name in pages:
    if name in root_public:
        continue
    if any(lk["attrs"].get("aria-current") for lk in pages[name].links):
        err(name, "這一頁不在導覽中，不應有 aria-current")
nav_hrefs = {lk["attrs"].get("href") for lk in pages["index.html"].links if lk["attrs"].get("href", "").startswith("/")}
if "articles.html" in pages and ("articles.html" in public) != ("/articles.html" in nav_hrefs):
    err("articles.html", "上線狀態不一致：articles.html 公開（index）時導覽必須有「文章」，未公開（noindex）時導覽不能有")
for name in root_public:
    cur = [lk for lk in pages[name].links if lk["attrs"].get("aria-current") == "page"]
    expect = "/" if name == "index.html" else "/" + name
    if len(cur) != 1 or cur[0]["attrs"].get("href") != expect:
        err(name, f'導覽必須恰好有一個 aria-current="page"，且指向 {expect}')

# ---------------------------------------------------------------- 3. sitemap／robots
sm = ROOT / "sitemap.xml"
if not sm.exists():
    err("sitemap.xml", "不存在，請執行 python3 authoring/build-sitemap.py")
else:
    locs = set(re.findall(r"<loc>(.*?)</loc>", sm.read_text(encoding="utf-8")))
    for name in pages:
        if name == "404.html":
            continue
        u = f"https://{domain}/" if name == "index.html" else f"https://{domain}/{name}"
        if name in public and u not in locs:
            err("sitemap.xml", f"缺少 {u}（請執行 python3 authoring/build-sitemap.py）")
        if name not in public and u in locs:
            err("sitemap.xml", f"不應收錄 noindex 頁面 {u}（請執行 python3 authoring/build-sitemap.py）")
    if any("404" in u for u in locs):
        err("sitemap.xml", "不應收錄 404")
robots = (ROOT / "robots.txt").read_text(encoding="utf-8") if (ROOT / "robots.txt").exists() else ""
if f"https://{domain}/sitemap.xml" not in robots:
    err("robots.txt", "Sitemap 網址與 CNAME 不一致")

# ---------------------------------------------------------------- 4. CSS：色票對比與單位
css = (ROOT / "assets/css/style.css").read_text(encoding="utf-8")


def lum(hexc: str) -> float:
    h = hexc.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z0-9-]+):\s*(#[0-9a-fA-F]{6})", block))


sets: dict[str, dict[str, str]] = {}


def block(pattern: str) -> dict[str, str]:
    m = re.search(pattern, css, re.S)
    return tokens(m.group(1)) if m else {}


sets["預設"] = block(r":root\s*\{(.*?)\}")
sets["深色（按鈕）"] = block(r':root\[data-theme="dark"\]\s*\{(.*?)\}')
sets["深色（系統）"] = block(r"prefers-color-scheme: dark\)\s*\{\s*:root:not\(\[data-theme\]\)\s*\{(.*?)\}")
sets["高對比（按鈕）"] = block(r':root\[data-theme="high"\]\s*\{(.*?)\}')
sets["高對比（系統）"] = block(r"prefers-contrast: more\)\s*\{\s*:root:not\(\[data-theme\]\)\s*\{(.*?)\}")

for a_, b_ in (("深色（按鈕）", "深色（系統）"), ("高對比（按鈕）", "高對比（系統）")):
    if sets[a_] != sets[b_]:
        err("style.css", f"兩份色票「{a_}」與「{b_}」不一致，請同步修改")

TEXT_PAIRS = [("text", "bg"), ("text", "surface"), ("text", "surface-2"), ("text", "accent-soft"),
              ("muted", "bg"), ("muted", "surface"), ("muted", "surface-2"),
              ("accent-ink", "bg"), ("accent-ink", "surface"), ("accent-ink", "surface-2"), ("accent-ink", "accent-soft"),
              ("on-accent", "accent"), ("paper", "ink")]
UI_PAIRS = [("border", "bg"), ("border", "surface"), ("border", "surface-2"), ("focus", "bg"), ("focus", "surface")]
NEED = {"bg", "surface", "surface-2", "text", "muted", "line", "border", "accent", "accent-soft", "accent-ink",
        "on-accent", "teal", "ink", "paper", "focus"}
for label, t in sets.items():
    if not NEED <= t.keys():
        err("style.css", f"{label} 色票缺少 token：{sorted(NEED - t.keys())}")
        continue
    for fg, bg in TEXT_PAIRS:
        r = ratio(t[fg], t[bg])
        if r < 7:
            err("style.css", f"{label}：文字 --{fg} 對 --{bg} 對比 {r:.2f}:1，未達 AAA（7:1）")
    for fg, bg in UI_PAIRS:
        r = ratio(t[fg], t[bg])
        if r < 3:
            err("style.css", f"{label}：介面元件 --{fg} 對 --{bg} 對比 {r:.2f}:1，未達 3:1")

for needle, why in (("@view-transition { navigation: auto; }", "切頁轉場"), ("nav-pill", "導覽膠囊滑動"),
                    ("@media (prefers-reduced-motion: reduce) {\n  @view-transition { navigation: none; }", "減少動態時關閉轉場")):
    if needle not in css:
        err("style.css", f"缺少{why}規則：{needle}")

for m in re.finditer(r"font-size:\s*([^;]+);", css):
    if "px" in m.group(1):
        err("style.css", f"font-size 不得使用 px（會無法隨使用者設定縮放）：{m.group(0)}")
if re.search(r"user-select:\s*none|outline:\s*(none|0)\b(?![^}]*:focus)", css) and "main:focus { outline: none; }" not in css:
    err("style.css", "不得移除焦點框或禁止選取文字")

# ---------------------------------------------------------------- 5. 分享圖與圖示檔案
og = ROOT / "assets/img/og.jpg"
if not og.exists():
    err("assets/img/og.jpg", "不存在，請執行 python3 authoring/build-og.py")
else:
    size = jpeg_size(og)
    if size != (1200, 630):
        err("assets/img/og.jpg", f"尺寸必須是 1200×630（目前 {size}）")
    if og.stat().st_size > 300 * 1024:
        err("assets/img/og.jpg", "檔案超過 300KB，請壓縮")
for f in ("assets/img/favicon.svg", "assets/img/apple-touch-icon.png", "assets/img/icon-192.png", "favicon.ico"):
    if not (ROOT / f).exists():
        err(f, "不存在（網站圖示來自品牌識別交件，請從交件包的 04_網站圖示 複製）")

# ---------------------------------------------------------------- 6. 首頁主視覺 SVG
HERO_PALETTES = {
    "light": {"#3A3A3C", "#E8695A", "#F2C230", "#FFF6EC"},
    "dark": {"#E8695A", "#F2C230", "#FFF6EC"},
    "high": {"#FFFFFF", "#FFFF00"},
}
for v, allowed in HERO_PALETTES.items():
    f = ROOT / "assets/img" / f"hero-{v}.svg"
    if not f.exists():
        err(f.name, "不存在（首頁主視覺需要 light／dark／high 三個版本）")
        continue
    svg = f.read_text(encoding="utf-8")
    if f.stat().st_size > 50 * 1024:
        err(f.name, "超過 50KB")
    if 'viewBox="0 0 600 800"' not in svg:
        err(f.name, 'viewBox 必須是 "0 0 600 800"')
    if re.search(r"<(text|image|script|style|filter|linearGradient|radialGradient)\b|href=", svg):
        err(f.name, "不得含 <text>、<image>、<script>、<style>、濾鏡、漸層、外部連結")
    if re.search(r"<svg[^>]*\s(width|height)=", svg):
        err(f.name, "最外層 <svg> 不得寫死 width／height，請只用 viewBox")
    used = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", svg)}
    if not used <= allowed:
        err(f.name, f"使用了色票以外的顏色：{sorted(used - allowed)}")
    for m in re.finditer(r'stroke-width="(\d+(?:\.\d+)?)"', svg):
        if float(m.group(1)) < 8:
            err(f.name, f"描邊 {m.group(1)} 小於 8，縮小後會消失")
if "hero-art" in css and not all(f"hero-{v}.svg" in css for v in HERO_PALETTES):
    err("style.css", "hero-art 必須同時引用 light／dark／high 三個版本")

# ---------------------------------------------------------------- 7. 品牌素材（橫式標誌、彩虹馬卡龍徽章、分享圖來源）
BRAND_ASSETS = {
    "assets/img/brand/lockup-dark.svg": {"#E8695A", "#3A3A3C"},
    "assets/img/brand/lockup-light.svg": {"#FFF6EC"},
    "assets/img/brand/lockup-rainbow.svg": None,   # 彩虹馬卡龍多色，不限制顏色，但不得有其他禁用元素
    "assets/img/brand/lockup-rainbow-clear.svg": None,
    "authoring/og/banner-coral.svg": {"#E8695A", "#EE8576", "#FFF6EC"},
}
for rel, allowed in BRAND_ASSETS.items():
    f = ROOT / rel
    if not f.exists():
        err(rel, "不存在（品牌素材來自品牌識別交件）")
        continue
    svg = f.read_text(encoding="utf-8")
    if f.stat().st_size > 60 * 1024:
        err(rel, "超過 60KB")
    if re.search(r"<(text|image|script|style|filter|linearGradient|radialGradient|mask|pattern)\b|href=", svg):
        err(rel, "不得含 <text>、<image>、<script>、<style>、濾鏡、漸層、遮色片、外部連結（文字必須已轉成路徑）")
    if allowed is not None:
        used = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", svg)}
        if not used <= allowed:
            err(rel, f"使用了色票以外的顏色：{sorted(used - allowed)}")
for needle in ("lockup-dark.svg", "lockup-light.svg", "lockup-rainbow.svg", "lockup-rainbow-clear.svg"):
    if needle not in css:
        err("style.css", f"必須引用品牌素材 {needle}")
# 彩虹馬卡龍只能出現在炭灰底的徽章內
if "lockup-rainbow.svg" in css and not re.search(r"\.badge-pride\s*\{[^}]*#3a3a3c[^}]*lockup-rainbow\.svg", css, re.I):
    err("style.css", "lockup-rainbow.svg 只能用在炭灰底（#3a3a3c）的 .badge-pride 內")
for name, pg in pages.items():
    for x, a in pg.tags:
        cls = a.get("class", "").split()
        if ("brand-lockup" in cls or "badge-pride" in cls) and a.get("aria-hidden") != "true":
            err(name, f'裝飾元素 .{ "brand-lockup" if "brand-lockup" in cls else "badge-pride" } 必須有 aria-hidden="true"')

# ---------------------------------------------------------------- 8. 說明性圖片（身分組示意圖）
mock = ROOT / "assets/img/roles-mock.svg"
if not mock.exists():
    err("assets/img/roles-mock.svg", "不存在（關於頁的身分組示意圖）")
else:
    svg = mock.read_text(encoding="utf-8")
    if mock.stat().st_size > 60 * 1024:
        err("roles-mock.svg", "超過 60KB")
    if re.search(r"<(image|script|style|filter|linearGradient|radialGradient|mask|pattern|foreignObject)\b|href=", svg):
        err("roles-mock.svg", "不得含 <image>、<script>、<style>、濾鏡、漸層、外部連結")
    if "<title" not in svg or "<desc" not in svg:
        err("roles-mock.svg", "需要 <title> 與 <desc>")
    used = {c.upper() for c in re.findall(r"#[0-9A-Fa-f]{6}\b", svg)}
    allowed = {"#232325", "#3A3A3C", "#4A4A4D", "#CFC8BC", "#E8695A", "#F2C230", "#FFF6EC"}
    if not used <= allowed:
        err("roles-mock.svg", f"使用了色票以外的顏色：{sorted(used - allowed)}")
    # 隱私：示意圖不得出現政黨名稱
    for bad in ("共產黨", "民進黨", "國民黨", "民眾黨", "時代力量", "綠黨", "社會民主黨", "親民黨", "新黨"):
        if bad in svg:
            err("roles-mock.svg", f"示意圖不得出現政黨名稱：{bad}")

# ---------------------------------------------------------------- 9. 文章（data/articles.json ⇄ articles/*.html）
articles = AL.load_articles()
by_slug = {a.get("slug"): a for a in articles}
if len(by_slug) != len(articles):
    err("data/articles.json", "slug 重複")
files = {Path(n).stem for n in pages if n.startswith("articles/")}
for slug in sorted(files - set(by_slug)):
    err(f"articles/{slug}.html", "沒有登錄在 data/articles.json（請用 authoring/md2article.py 產生）")
for slug in sorted(set(by_slug) - files):
    err("data/articles.json", f"{slug} 找不到 articles/{slug}.html")
known_actions = set(pages["actions.html"].ids) if "actions.html" in pages else set()
manifest = AL.load_manifest()
for slug, a in by_slug.items():
    where = f"data/articles.json（{slug}）"
    for k in ("title", "date", "category", "tags", "summary", "readingTime"):
        if not a.get(k):
            err(where, f"缺少 {k}")
    if not a.get("title") or not a.get("date") or not a.get("summary"):
        continue
    if not AL.SLUG_RE.fullmatch(str(slug)):
        err(where, "slug 只能是小寫英文、數字與連字號")
    for k in ("date", "updated"):
        if a.get(k) and not AL.DATE_RE.fullmatch(a[k]):
            err(where, f"{k} 格式必須是 YYYY-MM-DD")
    if a.get("updated") and a["updated"] < a["date"]:
        err(where, "updated 不能早於 date")
    if a.get("category") not in AL.CATEGORIES:
        err(where, f"category 必須是：{'、'.join(AL.CATEGORIES)}")
    if not 1 <= len(a.get("tags", [])) <= 3:
        err(where, "tags 必須是 1～3 個")
    if not 50 <= len(a["summary"]) <= 160:
        err(where, f"summary 應為 50～160 字（目前 {len(a['summary'])} 字）")
    if a.get("action") and a["action"] not in known_actions:
        err(where, f"action「{a['action']}」不是 actions.html 的錨點")
    extra = set(a) - {"slug", "title", "date", "category", "tags", "summary", "readingTime", "author", "updated", "draft", "action"}
    if extra:
        err(where, f"未知欄位：{sorted(extra)}")
    name = f"articles/{slug}.html"
    if name not in pages:
        continue
    pg = pages[name]
    raw = (ROOT / name).read_text(encoding="utf-8")
    full = f"{a['title']}｜{AL.SITE_NAME}"
    if pg.title.strip() != full:
        err(name, f"<title> 必須是「{full}」（與 data/articles.json 一致）")
    if pg.metas.get("description") != a["summary"]:
        err(name, "description 必須與 data/articles.json 的 summary 逐字一致")
    if pg.metas.get("og:type") != "article":
        err(name, 'og:type 必須是 "article"')
    if pg.metas.get("article:published_time") != a["date"]:
        err(name, "article:published_time 必須與 date 一致")
    if pg.metas.get("og:image:alt") != AL.og_alt(a["title"]):
        err(name, f"og:image:alt 必須是「{AL.og_alt(a['title'])}」")
    if f'data-slug="{slug}"' not in raw:
        err(name, f'缺少 <article data-slug="{slug}">')
    is_noindex = "noindex" in pg.metas.get("robots", "")
    if bool(a.get("draft")) != is_noindex:
        err(name, "draft 與 robots 不一致：草稿必須 noindex，正式文章必須 index")
    if f'href="/articles.html#{AL.CATEGORIES.get(a.get("category"), "")}"' not in raw:
        err(name, "分類標籤必須連到 /articles.html 的對應分類")
    if "<!--articlenav:start-->" not in raw:
        err(name, "缺少上一篇／下一篇的 articlenav 標記")
    try:
        graph = json.loads(pg.ldjson[0]).get("@graph", []) if pg.ldjson else []
        art = next(n for n in graph if n.get("@type") == "Article")
    except (ValueError, StopIteration):
        err(name, "JSON-LD 需要 @graph 內的 Article")
    else:
        want = {"headline": a["title"], "datePublished": a["date"], "dateModified": a.get("updated") or a["date"],
                "articleSection": a["category"]}
        for k, v in want.items():
            if art.get(k) != v:
                err(name, f"JSON-LD Article.{k} 應為 {v!r}（目前 {art.get(k)!r}）")
        au = art.get("author", {})
        if au.get("name") != AL.author_name(a) or au.get("@type") != ("Person" if a.get("author") else "Organization"):
            err(name, f"JSON-LD Article.author 應為 {AL.author_name(a)}")
    if AL.author_name(a) not in raw:
        err(name, "頁面沒有顯示作者")
    # 分享圖
    og_file = AL.OG_DIR / f"{slug}.jpg"
    if not og_file.exists():
        err(name, f"缺少分享圖 {og_file.relative_to(ROOT)}（請執行 python3 authoring/build-og.py {slug}）")
    else:
        if jpeg_size(og_file) != (1200, 630):
            err(str(og_file.relative_to(ROOT)), "尺寸必須是 1200×630")
        if og_file.stat().st_size > 300 * 1024:
            err(str(og_file.relative_to(ROOT)), "檔案超過 300KB")
        if manifest.get(slug) != AL.og_hash(a):
            err(str(og_file.relative_to(ROOT)), f"分享圖過期（標題、分類或卡片範本改過；請執行 python3 authoring/build-og.py {slug}）")
for f in sorted(AL.OG_DIR.glob("*")) if AL.OG_DIR.exists() else []:
    if f.suffix != ".jpg" or f.stem not in by_slug:
        err(str(f.relative_to(ROOT)), "沒有對應的文章（請執行 python3 authoring/build-og.py --articles 清除）")
for script, what in (("build-lists.py", "文章列表"), ("build-feed.py", "訂閱源")):
    r = subprocess.run([sys.executable, str(ROOT / "authoring" / script), "--check"], capture_output=True, text=True)
    if r.returncode:
        err(script, (r.stderr.strip() or f"{what}過期") + "")

# ---------------------------------------------------------------- 10. 成員數（build-members.py 寫入的靜態文字）
for name, keys in (("index.html", ("count",)), ("about.html", ("count", "date"))):
    text = (ROOT / name).read_text(encoding="utf-8")
    for k in keys:
        if not re.search(rf"<!--members:{k}-->[^<]+<!--/members:{k}-->", text):
            err(name, f"缺少或清空了 <!--members:{k}--> 標記（成員數由 authoring/build-members.py 寫入）")

# ---------------------------------------------------------------- 結果
if errors:
    print(f"✗ 發現 {len(errors)} 個問題：", file=sys.stderr)
    for e in errors:
        print("  - " + e, file=sys.stderr)
    sys.exit(1)
print(f"✓ 檢查通過（{len(pages)} 頁，其中 {len(files)} 篇文章；5 組色票）")
