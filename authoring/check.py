#!/usr/bin/env python3
"""網站品質與無障礙檢查。CI 與 pre-commit 都會執行；任何問題都會列出後以非 0 結束。

檢查：頁面結構與地標、標題層級、跳過連結、外部資源、連結與錨點、導覽／頁尾一致、
meta 一致、sitemap、CSS 色票對比（WCAG 相對亮度）、字級單位。
"""
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

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.tags.append((tag, a))
        if tag == "html":
            self.lang = a.get("lang", "")
        if tag == "title":
            self._in_title = True
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
        if tag == "a" and self._cur_a is not None:
            self.links.append(self._cur_a)
            self._cur_a = None
        if self._stack and ((tag in ("header", "footer") and self._stack[-1] == tag) or (tag == "section" and self._stack[-1] == "prefs")):
            self._stack.pop()

    def handle_data(self, data):
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
        if s.get("src") != "/assets/js/prefs.js":
            err(name, f"只允許載入 /assets/js/prefs.js（發現：{s}）")
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

# ---------------------------------------------------------------- 結果
if errors:
    print(f"✗ 發現 {len(errors)} 個問題：", file=sys.stderr)
    for e in errors:
        print("  - " + e, file=sys.stderr)
    sys.exit(1)
print(f"✓ 檢查通過（{len(pages)} 頁、5 組色票）")
