#!/usr/bin/env python3
"""網站品質與無障礙檢查。CI 與 pre-commit 都會執行；任何問題都會列出後以非 0 結束。

檢查：頁面結構與地標、標題層級、跳過連結、外部資源、連結與錨點、導覽／頁尾一致、
meta 一致、sitemap、CSS 色票對比（WCAG 相對亮度）、字級單位。
"""
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
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
html_files = sorted(ROOT.glob("*.html"))
pages = {p.name: load(p) for p in html_files}
public = [n for n in pages if n != "404.html"]


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
    elif not robots.startswith("index,follow"):
        err(name, '缺少 <meta name="robots" content="index,follow,…">')
    desc = m.get("description", "")
    if name != "404.html" and not 50 <= len(desc) <= 160:
        err(name, f"description 長度應為 50～160 字（目前 {len(desc)} 字）")
    # 社群分享
    img = f"{base}/assets/img/og.jpg"
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
            last = nodes[0]["itemListElement"][-1]["item"]
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
            if "alt" not in a:
                err(name, "<img> 缺少 alt")
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
            if target_name not in pages:
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

# 導覽：恰好一個 aria-current，且指向自己
for name in public:
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
    for name in public:
        u = f"https://{domain}/" if name == "index.html" else f"https://{domain}/{name}"
        if u not in locs:
            err("sitemap.xml", f"缺少 {u}")
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
for f in ("assets/img/favicon.svg", "assets/img/apple-touch-icon.png", "favicon.ico"):
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

# ---------------------------------------------------------------- 結果
if errors:
    print(f"✗ 發現 {len(errors)} 個問題：", file=sys.stderr)
    for e in errors:
        print("  - " + e, file=sys.stderr)
    sys.exit(1)
print(f"✓ 檢查通過（{len(pages)} 頁、5 組色票）")
