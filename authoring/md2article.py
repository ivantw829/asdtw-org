#!/usr/bin/env python3
"""Markdown → 文章頁（移植自 me.asdtw.org，改成完全靜態、不依賴 JS）。

做的事（輸出是提交進 repo 的靜態 HTML）：
  1. 產生 articles/<slug>.html（套 authoring/article-template.html；閱讀設定、頁首、頁尾從 index.html 逐字複製）
  2. 新增／更新 data/articles.json 的該筆資料
  3. 處理圖片（給 --images 時）：png／jpg 用 cwebp 轉成 webp 放到 assets/img/articles/<slug>/，
     最寬 1600px、品質自動調整到 ≤300KB；webp 原檔直接複製
  4. 產生分享圖、sitemap、feed.xml、列表與上下篇，最後執行 check.py

用法：
  python3 authoring/md2article.py 原稿.md [--images 圖片資料夾]

原稿格式（範例見 authoring/article-sample.md）：
  ---
  title: 文章標題
  slug: my-article            # 小寫英文、數字、連字號
  date: 2026-11-20
  category: 行動記事          # 行動記事／社群公告／議題觀點／技術教學（定義在 authoring/articles_lib.py）
  tags: 標籤1, 標籤2          # 1～3 個副標籤。先看 data/articles.json 已有哪些，意思相近就沿用
  summary: 50～160 字摘要，同時用在 description／og:description／列表
  lead: 一句話導言（30～60 字），顯示在標題下
  author: 筆名               # 選填：沒填就是「福爾摩沙自閉大公社」
  action: pride-2026          # 選填：actions.html 的行動 id，文章頁會顯示「相關行動」連結
  readingTime: 6              # 選填，沒填就以每分鐘 400 字估算
  updated: 2026-12-01         # 選填：發布後修改過才填
  draft: true                 # 選填：草稿。不進列表／sitemap／feed，頁面 noindex；拿掉後重跑就是正式發布
  ---

譯文（英／日文版）：同一份格式另寫一份原稿，frontmatter 加 `lang: en` 或 `lang: ja`，slug 與中文原文相同，
  只填 title、slug、lang、tags（譯名）、summary、lead，選填 readingTime、updated；日期、分類、作者、行動沿用原文
  （原文必須先上架）。產生 en/articles/<slug>.html 或 ja/articles/<slug>.html，登錄在原文的 translations 欄位。
  內文的 `## 參考資料` 依語系寫成 `## References`／`## 参考資料`；`[[目錄]]` 等標記照用中文寫法。
  內文 Markdown。支援：
    ## 大標、### 小標、#### 小小標、段落、- 清單、1. 清單、| 表格 |、> 引言、--- 分隔線、```程式碼區塊```
    ![替代文字](檔名.png "圖說")  # 輸出一律 .webp。只放示意圖，不放現場照片或社員截圖
                              # 省略 "圖說" 時替代文字兼作圖說；兩者都有時報讀器才不會重複念同一段
    [[提示框：標題]] 下一段文字（到空行為止）
    [[金句：一句話]]
    [[目錄]]                  # 在第一個大標前產生目錄
    `code`、**粗體**、[文字](網址)、裸網址（外部連結自動加「（另開新視窗）」）
    最後可放 `## 參考資料` + 編號清單，會變成文末參考資料區塊
"""
import difflib
import html
import json
import re
import shutil
import struct
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402
import i18n as I  # noqa: E402

ROOT = L.ROOT
TEMPLATE = ROOT / "authoring" / "article-template.html"
MAX_IMG_KB = 300
MAX_W = 1600
IMG_EXT = (".png", ".jpg", ".jpeg")
LOC = "zh"  # 目前產生的語系；main() 依 frontmatter 的 lang 設定
NEW_WINDOW = I.fmt_external_suffix("zh")


def S(key: str) -> str:
    """文章頁的介面文字（authoring/i18n.py 的 LOCALES[語系]["article"]）。"""
    return I.LOCALES[LOC]["article"][key]


def die(msg: str) -> None:
    sys.exit(f"✗ {msg}")


# ---------------------------------------------------------------- 圖片
def webp_size(path: Path):
    d = path.read_bytes()[:40]
    if d[:4] != b"RIFF" or d[8:12] != b"WEBP":
        return None
    kind = d[12:16]
    if kind == b"VP8 ":
        w, h = struct.unpack("<HH", d[26:30])
        return w & 0x3FFF, h & 0x3FFF
    if kind == b"VP8L":
        b = struct.unpack("<I", d[21:25])[0]
        return (b & 0x3FFF) + 1, ((b >> 14) & 0x3FFF) + 1
    if kind == b"VP8X":
        return int.from_bytes(d[24:27], "little") + 1, int.from_bytes(d[27:30], "little") + 1
    return None


def to_webp(src: Path, dst: Path) -> None:
    cwebp = shutil.which("cwebp")
    if not cwebp:
        die("找不到 cwebp，請先安裝：brew install webp（或先把圖片轉成 webp 再放進 --images 資料夾）")
    out = subprocess.run(["sips", "-g", "pixelWidth", str(src)], capture_output=True, text=True).stdout
    m = re.search(r"pixelWidth: (\d+)", out)
    args = ["-resize", str(MAX_W), "0"] if m and int(m.group(1)) > MAX_W else []
    dst.parent.mkdir(parents=True, exist_ok=True)
    for q in (88, 80, 72, 64, 56, 48, 40):
        subprocess.run([cwebp, "-quiet", "-q", str(q), *args, str(src), "-o", str(dst)], check=True)
        if dst.stat().st_size <= MAX_IMG_KB * 1024:
            return
    print(f"! {dst.name}：壓到最低品質仍有 {dst.stat().st_size // 1024}KB（建議 ≤{MAX_IMG_KB}KB），請換較小的原圖")


def normalize_refs(body: str) -> str:
    """![](x.png) → ![](x.webp)"""
    def fix(m):
        name = m.group(2)
        if re.match(r"https?://", name):
            die(f"不得引用外部圖片（本站不載入外部資源）：{name}")
        stem, ext = (name.rsplit(".", 1) + [""])[:2]
        if ext.lower() in ("png", "jpg", "jpeg", "webp"):
            name = f"{stem}.webp"
        return f"![{m.group(1)}]({name}{m.group(3)})"
    return re.sub(r'!\[(.*?)\]\(([^)\s]*)((?:\s+"[^"]*")?)\)', fix, body)


def prepare_images(body: str, slug: str, images_dir):
    """依原稿引用的圖片處理檔案，回傳 {檔名: (寬, 高)}。"""
    refs = sorted(set(re.findall(r'!\[.*?\]\(([^)/\s]+\.webp)(?:\s+"[^"]*")?\)', body)))
    if refs:
        print("! 提醒：本站不放現場照片與社員截圖；說明用的圖請重畫成示意圖，並在圖說標明「示意圖」。")
    out_dir = ROOT / "assets" / "img" / "articles" / slug
    dims = {}
    for f in refs:
        dst = out_dir / f
        stem = f[:-5]
        if images_dir:
            cands = [images_dir / f, *[images_dir / (stem + e) for e in IMG_EXT],
                     *[images_dir / (stem + e.upper()) for e in IMG_EXT]]
            src = next((c for c in cands if c.exists()), None)
            if src is None:
                print(f"! 在 {images_dir} 找不到 {stem}.(webp|png|jpg)")
            elif src.suffix.lower() == ".webp":
                out_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            else:
                to_webp(src, dst)
                print(f"  ✓ {src.name} → {dst.relative_to(ROOT)}（{dst.stat().st_size // 1024}KB）")
        if not dst.exists():
            die(f"缺少圖片 {dst.relative_to(ROOT)}（請用 --images 指定圖片資料夾）")
        size = webp_size(dst)
        if not size:
            die(f"{dst.relative_to(ROOT)} 不是有效的 webp")
        dims[f] = size
        if dst.stat().st_size > MAX_IMG_KB * 1024:
            print(f"! {f}：{dst.stat().st_size // 1024}KB 超過建議的 {MAX_IMG_KB}KB")
    return dims


def tag_warnings(tags, others):
    known = sorted({t for a in others for t in a.get("tags", [])})
    new = [t for t in tags if t not in known]
    if new and known:
        print(f"! 新標籤 {new}；既有標籤：{'、'.join(known)}。意思相近請改用既有的。")
    for t in new:
        near = difflib.get_close_matches(t, known, n=1, cutoff=0.6)
        if near:
            print(f"! 標籤「{t}」是新的，但跟既有標籤「{near[0]}」很像，要統一用詞嗎？")


# ---------------------------------------------------------------- Markdown
def parse_frontmatter(text: str):
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        die("原稿開頭必須有 --- frontmatter ---")
    fm = {}
    for line in m.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, _, v = line.partition(":")
        v = re.sub(r"\s+#.*$", "", v).strip()  # 允許行尾註解
        fm[k.strip()] = v
    return fm, m.group(2)


def inline(t: str) -> str:
    t = re.sub(r"<(https?://[^>\s]+)>", r"\1", t)
    t = html.escape(t, quote=False)
    stash = []

    def keep(s: str) -> str:
        stash.append(s)
        return f"\x00{len(stash) - 1}\x00"

    t = re.sub(r"`([^`]+)`", lambda m: keep(f"<code>{m.group(1)}</code>"), t)

    def link(m):
        text, href = m.group(1), m.group(2)
        if href.startswith("http://"):
            die(f"外部連結請用 https：{href}")
        if href.startswith("https://") and f"//{L.domain()}" not in href:
            return keep(f'<a href="{href.replace(chr(34), "&quot;")}" target="_blank" rel="noopener">{text}{NEW_WINDOW}</a>')
        return keep(f'<a href="{href.replace(chr(34), "&quot;")}">{text}</a>')

    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", link, t)
    t = re.sub(r"(https://[^\s<）」，。、；：]+)",
               lambda m: keep(f'<a href="{m.group(1)}" target="_blank" rel="noopener">{m.group(1)}{NEW_WINDOW}</a>'), t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    while "\x00" in t:
        t = re.sub(r"\x00(\d+)\x00", lambda m: stash[int(m.group(1))], t)
    return t


def plain(t: str) -> str:
    """標題的純文字（給 aria-label 用）"""
    return html.unescape(re.sub(r"<[^>]+>", "", inline(t))).replace(NEW_WINDOW, "").strip()


def convert(body: str, slug: str, dims):
    """回傳 (內文 HTML, 參考資料清單)"""
    lines = body.strip("\n").split("\n")
    out, h2s = [], []
    sources = None
    want_toc = False
    tables = 0
    last_head, head_tables = "", {}  # 表格的區域名稱用最近的標題，報讀器才知道是哪張表
    seen_h3 = -1  # 最近一個 ### 所屬的 ## 序號，用來擋 ## 之後直接 ####
    i = 0
    while i < len(lines):
        s = lines[i].strip()
        if not s:
            i += 1
            continue
        if s.startswith("```"):
            i += 1
            code = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + html.escape("\n".join(code), quote=False) + "</code></pre>")
            continue
        if s == "[[目錄]]":
            want_toc = True
            i += 1
            continue
        if s == "---":
            out.append("<hr>")
            i += 1
            continue
        m = re.match(r'!\[(.*?)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)$', s)
        if m:
            alt, fname, cap = m.group(1).strip(), m.group(2), (m.group(3) or "").strip()
            if not alt:
                die(f"圖片 {fname} 缺少替代文字（![替代文字](檔名 \"圖說\")），不能空白")
            w, h = dims[fname]
            a, c = html.escape(alt), html.escape(cap or alt)
            out.append(f'<figure class="figure">\n  <img src="/assets/img/articles/{slug}/{fname}" alt="{a}" '
                       f'loading="lazy" width="{w}" height="{h}">\n  <figcaption>{c}</figcaption>\n</figure>')
            i += 1
            continue
        m = re.match(r"\[\[提示框：(.*?)\]\]$", s)
        if m:
            i += 1
            ps = []
            while i < len(lines) and lines[i].strip():
                ps.append(lines[i].strip())
                i += 1
            out.append(f'<div class="note">\n  <p class="note-title">{inline(m.group(1))}</p>\n'
                       + "\n".join(f"  <p>{inline(p)}</p>" for p in ps) + "\n</div>")
            continue
        m = re.match(r"\[\[金句：(.*?)\]\]$", s)
        if m:
            out.append(f'<p class="pullquote">{inline(m.group(1))}</p>')
            i += 1
            continue
        if s.startswith("## "):
            title = s[3:].strip()
            if title in ("參考資料", S("sources")):
                i += 1
                items = []
                while i < len(lines) and not lines[i].startswith("## "):
                    mm = re.match(r"\d+\. (.*)", lines[i].strip())
                    if mm:
                        items.append(mm.group(1))
                    i += 1
                sources = items
                continue
            h2s.append(title)
            last_head = plain(title)
            if len(h2s) == 1 and want_toc:
                out.append("@@TOC@@")
            out.append(f'<h2 id="s{len(h2s)}">{inline(title)}</h2>')
            i += 1
            continue
        if s.startswith("### "):
            if not h2s:
                die(f"「{s}」：### 小標前必須先有 ## 大標（標題不能跳級）")
            out.append(f"<h3>{inline(s[4:])}</h3>")
            last_head = plain(s[4:])
            seen_h3 = len(h2s)
            i += 1
            continue
        if s.startswith("#### "):
            if seen_h3 != len(h2s) or not h2s:
                die(f"「{s}」：#### 小標前必須先有 ### 小標（標題不能跳級）")
            out.append(f"<h4>{inline(s[5:])}</h4>")
            last_head = plain(s[5:])
            i += 1
            continue
        if s.startswith(">"):
            qs = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                qs.append(lines[i].strip().lstrip(">").strip())
                i += 1
            cite = qs.pop() if len(qs) > 1 and qs[-1].startswith(("—", "－")) else None
            out.append("<blockquote>\n" + "\n".join(f"  <p>{inline(q)}</p>" for q in qs if q)
                       + (f"\n  <cite>{inline(cite)}</cite>" if cite else "") + "\n</blockquote>")
            continue
        if s.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(lines[i].strip())
                i += 1
            cells = lambda r: [c.strip() for c in r.strip("|").split("|")]  # noqa: E731
            head, rest = cells(rows[0]), [cells(r) for r in rows[2:]]
            tables += 1
            head_tables[last_head] = head_tables.get(last_head, 0) + 1
            n = head_tables[last_head]
            colon = ": " if LOC == "en" else "："
            label = (f"{S('table')}{' ' + str(n) if n > 1 else ''}{colon}{last_head}" if last_head else f"{S('table')} {tables}")
            out.append(f'<div class="table-wrap" role="region" aria-label="{html.escape(label)}{S("scroll")}" tabindex="0">\n'
                       "<table>\n  <thead><tr>" + "".join(f'<th scope="col">{inline(c)}</th>' for c in head)
                       + "</tr></thead>\n  <tbody>\n"
                       + "\n".join("    <tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in rest)
                       + "\n  </tbody>\n</table>\n</div>")
            continue
        if re.match(r"(- |\d+\. )", s):
            tag = "ul" if s.startswith("- ") else "ol"
            items = []
            while i < len(lines) and re.match(r"(- |\d+\. )", lines[i].strip()):
                items.append(re.sub(r"^(- |\d+\. )", "", lines[i].strip()))
                i += 1
            out.append(f"<{tag}>\n" + "\n".join(f"  <li>{inline(x)}</li>" for x in items) + f"\n</{tag}>")
            continue
        out.append(f"<p>{inline(s)}</p>")
        i += 1

    toc = ""
    if want_toc and h2s:
        toc = (f'<nav class="note toc" aria-label="{S("toc")}">\n  <p class="note-title">{S("toc")}</p>\n  <ol>\n'
               + "\n".join(f'    <li><a href="#s{n + 1}">{inline(t)}</a></li>' for n, t in enumerate(h2s))
               + "\n  </ol>\n</nav>")
    return "\n\n".join(out).replace("@@TOC@@", toc), sources


# ---------------------------------------------------------------- 組頁
def ldjson(a: dict) -> str:
    url, b = L.article_url(a["slug"], LOC), L.base()
    org = {"@type": "Organization", "name": L.site_name(LOC), "url": I.page_url(b, LOC, "index.html")}
    author = {"@type": "Person", "name": a["author"]} if a.get("author") else org
    data = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": a["title"], "description": a["summary"],
         "datePublished": a["date"], "dateModified": a.get("updated") or a["date"],
         "inLanguage": I.LOCALES[LOC]["html_lang"], "articleSection": I.LOCALES[LOC]["categories"][a["category"]],
         "keywords": (", " if LOC == "en" else "、").join(a["tags"]),
         "image": [L.og_url(a["slug"], LOC)], "mainEntityOfPage": url, "author": author,
         "publisher": {**org, "logo": f"{b}/assets/img/icon-192.png"}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": S("home"), "item": I.page_url(b, LOC, "index.html")},
            {"@type": "ListItem", "position": 2, "name": {"zh": "文章", "en": "Articles", "ja": "記事"}[LOC],
             "item": I.page_url(b, LOC, "articles.html")},
            {"@type": "ListItem", "position": 3, "name": a["title"], "item": url}]},
    ]}
    return json.dumps(data, ensure_ascii=False, indent=2).replace("</", "<\\/")


def build(a: dict, lead: str, body_html: str, sources) -> str:
    e = L.esc
    info = I.LOCALES[LOC]
    t = TEMPLATE.read_text(encoding="utf-8")
    t = re.sub(r"<!--\n.*?-->\n", "", t, count=1, flags=re.S)  # 移除範本說明
    shared = L.shared_blocks(L.article_rel(a["slug"], LOC))
    sep = '<span aria-hidden="true"> · </span>'
    meta = (f'<time datetime="{a["date"]}">{I.fmt_date(a["date"], LOC)}</time>{sep}'
            f'{S("by")}{e(L.author_name(a, LOC))}{sep}{I.fmt_reading_time(a["readingTime"], LOC)}')
    if a.get("updated"):
        meta += f'{sep}{S("updated")}<time datetime="{a["updated"]}">{I.fmt_date(a["updated"], LOC)}</time>'
    metas = []
    if a.get("updated"):
        metas.append(f'<meta property="article:modified_time" content="{a["updated"]}">')
    cat = a["category"]
    cat_name = info["categories"][cat]
    metas.append(f'<meta property="article:section" content="{e(cat_name)}">')
    metas += [f'<meta property="article:tag" content="{e(x)}">' for x in a["tags"]]
    tags = (f'<span class="visually-hidden">{S("category")}</span>'
            f'<a class="tag" href="{I.page_href(LOC, "articles.html")}#{L.CATEGORIES[cat]}">{e(cat_name)}</a>'
            f'<span class="visually-hidden">{S("tags")}</span>'
            + "".join(f'<span class="tag tag-sub">{e(x)}</span>' for x in a["tags"]))
    action = ""
    if a.get("action"):
        title = L.action_title(a["action"], LOC)
        action = (f'        <p class="article-action">{S("action")}<a href="{I.page_href(LOC, "actions.html")}#{a["action"]}">'
                  f'{e(title)}</a></p>')
    note = ""
    if LOC != "zh":
        note = f'        <p class="article-translation muted">{S("translation_note").format(href="/" + L.article_rel(a["slug"]))}</p>'
    draft = ""
    if a.get("draft"):
        draft = f'      <div class="note">\n        <p>{S("draft")}</p>\n      </div>'
    src = ""
    if sources:
        src = ('      <aside class="article-sources" aria-labelledby="sources-title">\n'
               f'        <h2 id="sources-title">{S("sources")}</h2>\n        <ol>\n'
               + "\n".join(f"          <li>{inline(x)}</li>" for x in sources)
               + "\n        </ol>\n      </aside>")
    pres = []
    body = re.sub(r"<pre>.*?</pre>", lambda m: pres.append(m.group(0)) or f"@@PRE{len(pres) - 1}@@", body_html, flags=re.S)
    body = "\n".join((" " * 8 + x if x else x) for x in body.split("\n"))
    body = re.sub(r"@@PRE(\d+)@@", lambda m: pres[int(m.group(1))], body)
    rep = {
        "TITLE": e(a["title"]), "PAGE_TITLE": e(L.page_title(a["title"], LOC)), "SUMMARY": e(a["summary"]),
        "URL": L.article_url(a["slug"], LOC), "ALTERNATES": "",
        "HTML_LANG": info["html_lang"], "OG_LOCALE": info["og_locale"], "SITE_NAME": e(info["site_name"]),
        "FEED_TITLE": e(S("feed")), "SKIP": e(info["skip_link"]), "NAV_LABEL": e(S("nav")),
        "ROBOTS": "noindex,follow" if a.get("draft") else "index,follow,max-image-preview:large",
        "OG_IMAGE": L.og_url(a["slug"], LOC), "OG_ALT": e(L.og_alt(a["title"], LOC)), "DATE": a["date"],
        "ARTICLE_METAS": "\n".join(metas), "LDJSON": ldjson(a), "SLUG": a["slug"],
        "PREFS": shared["prefs"], "HEADER": shared["header"], "FOOTER": shared["footer"],
        "TAGS": tags, "LEAD": e(lead), "META": meta, "ACTION": action, "TRANSLATION_NOTE": note, "DRAFT_NOTE": draft,
        "BODY": body, "SOURCES": src,
    }
    # 獨占一行的選填區塊：沒有內容就連同整行刪除
    t = re.sub(r"^\{\{([A-Z_]+)\}\}\n", lambda m: rep[m.group(1)] + "\n" if rep[m.group(1)] else "", t, flags=re.M)
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: rep[m.group(1)], t)


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    images_dir = None
    if "--images" in args:
        k = args.index("--images")
        images_dir = Path(args[k + 1]).expanduser()
        del args[k:k + 2]
    fm, body = parse_frontmatter(Path(args[0]).expanduser().read_text(encoding="utf-8"))
    if fm.get("lang"):
        return main_translation(fm, body, images_dir)
    for k in ("title", "slug", "date", "category", "tags", "summary", "lead"):
        if not fm.get(k):
            die(f"frontmatter 缺少 {k}")
    if fm["category"] not in L.CATEGORIES:
        die(f"category「{fm['category']}」不在允許清單：{'、'.join(L.CATEGORIES)}")
    slug = fm["slug"]
    if not L.SLUG_RE.fullmatch(slug):
        die("slug 只能是小寫英文、數字與連字號")
    for k in ("date", "updated"):
        if fm.get(k) and not L.DATE_RE.fullmatch(fm[k]):
            die(f"{k} 格式必須是 YYYY-MM-DD")
    if fm.get("updated") and fm["updated"] < fm["date"]:
        die("updated 不能早於 date")
    if fm.get("action") and not L.action_title(fm["action"]):
        die(f"actions.html 沒有 id 為「{fm['action']}」的行動")
    tags = [x.strip() for x in re.sub(r"^\[|\]$", "", fm["tags"]).split(",") if x.strip()]
    if not 1 <= len(tags) <= 3:
        die("標籤必須是 1～3 個")
    if not 50 <= len(fm["summary"]) <= 160:
        die(f"summary 必須是 50～160 字（目前 {len(fm['summary'])} 字）")
    for k in ("title", "summary", "lead"):
        if "捍衛全台學權行動" in fm[k] or "捍衛全台學權行動" in body:
            die("網站上不得出現「捍衛全台學權行動」（內容守則）")

    body = normalize_refs(body)
    dims = prepare_images(body, slug, images_dir)
    body_html, sources = convert(body, slug, dims)
    text_len = len(re.sub(r"\s|<[^>]+>", "", body_html))
    rt = int(fm["readingTime"]) if fm.get("readingTime") else max(1, round(text_len / 400))

    entry = {"slug": slug, "title": fm["title"], "date": fm["date"], "category": fm["category"], "tags": tags,
             "summary": fm["summary"], "readingTime": rt}
    for k in ("author", "action", "updated"):
        if fm.get(k):
            entry[k] = fm[k]
    if fm.get("draft", "").lower() == "true":
        entry["draft"] = True

    data = L.load_articles()
    tag_warnings(tags, [a for a in data if a["slug"] != slug])
    out = L.ARTICLES_DIR / f"{slug}.html"
    existed = out.exists()
    out.parent.mkdir(exist_ok=True)
    out.write_text(build(entry, fm["lead"], body_html, sources), encoding="utf-8")
    print(f"{'更新' if existed else '建立'} {out.relative_to(ROOT)}（閱讀約 {rt} 分鐘）")
    if entry.get("draft"):
        print("! 草稿：不會出現在列表、sitemap 與 feed，但知道網址的人仍看得到頁面，不要放敏感內容。")

    for k, a in enumerate(data):
        if a["slug"] == slug:
            if a.get("translations"):
                entry["translations"] = a["translations"]  # 重新產生原文時保留譯文登錄
                print("! 這篇有譯文（" + "、".join(a["translations"]) + "）：原文內容改了的話，譯文也要跟著改並重新產生。")
            data[k] = entry
            break
    else:
        data.append(entry)
    data.sort(key=lambda a: (a["date"], a["slug"]))
    L.save_articles(data)

    py, au = sys.executable, ROOT / "authoring"
    subprocess.run([py, str(au / "build-og.py"), slug], check=True)
    rebuild()


def rebuild() -> None:
    py, au = sys.executable, ROOT / "authoring"
    subprocess.run([py, str(au / "build-shared.py")], check=True)  # 語言切換器依譯文是否存在而變
    subprocess.run([py, str(au / "build-lists.py")], check=True)
    subprocess.run([py, str(au / "build-feed.py")], check=True)
    subprocess.run([py, str(au / "build-sitemap.py")], check=True)
    sys.exit(subprocess.run([py, str(au / "check.py")]).returncode)


def main_translation(fm: dict, body: str, images_dir) -> None:
    """英／日文譯文：登錄在原文的 translations.<語系>，產生 <語系>/articles/<slug>.html。"""
    global LOC, NEW_WINDOW
    loc = fm["lang"]
    if loc not in L.TRANSLATION_LOCALES:
        die(f"lang 必須是 {'、'.join(L.TRANSLATION_LOCALES)}（中文原文不寫 lang）")
    LOC, NEW_WINDOW = loc, I.fmt_external_suffix(loc)
    for k in ("title", "slug", "tags", "summary", "lead"):
        if not fm.get(k):
            die(f"frontmatter 缺少 {k}")
    for k in ("date", "category", "author", "action", "draft"):
        if fm.get(k):
            die(f"譯文不寫 {k}：日期、分類、作者、行動與草稿狀態沿用中文原文")
    slug = fm["slug"]
    data = L.load_articles()
    src = next((a for a in data if a["slug"] == slug and not L.is_external(a)), None)
    if src is None:
        die(f"data/articles.json 沒有 {slug}：請先上架中文原文，譯文的 slug 要與原文相同")
    if fm.get("updated"):
        if not L.DATE_RE.fullmatch(fm["updated"]):
            die("updated 格式必須是 YYYY-MM-DD")
        if fm["updated"] < src["date"]:
            die("updated 不能早於原文的 date")
    tags = [x.strip() for x in re.sub(r"^\[|\]$", "", fm["tags"]).split(",") if x.strip()]
    if len(tags) != len(src["tags"]):
        die(f"標籤數量要與原文相同（原文：{'、'.join(src['tags'])}），逐一翻譯")
    if not 50 <= len(fm["summary"]) <= 160:
        die(f"summary 必須是 50～160 字元（目前 {len(fm['summary'])}）")
    for k in ("title", "summary", "lead"):
        if "捍衛全台學權行動" in fm[k] or "捍衛全台學權行動" in body:
            die("網站上不得出現「捍衛全台學權行動」（內容守則）")

    body = normalize_refs(body)
    dims = prepare_images(body, slug, images_dir)
    body_html, sources = convert(body, slug, dims)
    if fm.get("readingTime"):
        rt = int(fm["readingTime"])
    else:
        text = re.sub(r"<[^>]+>", " ", body_html)
        rt = max(1, round(len(text.split()) / 200)) if loc == "en" else max(1, round(len(re.sub(r"\s", "", text)) / 500))
    tr = {"title": fm["title"], "summary": fm["summary"], "tags": tags, "readingTime": rt}
    if fm.get("updated"):
        tr["updated"] = fm["updated"]
    src.setdefault("translations", {})[loc] = tr
    src["translations"] = {k: src["translations"][k] for k in L.TRANSLATION_LOCALES if k in src["translations"]}
    entry = L.localized(src, loc)

    out = L.article_path(slug, loc)
    existed = out.exists()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(entry, fm["lead"], body_html, sources), encoding="utf-8")
    print(f"{'更新' if existed else '建立'} {out.relative_to(ROOT)}（{I.fmt_reading_time(rt, loc)}）")
    L.save_articles(data)

    py, au = sys.executable, ROOT / "authoring"
    subprocess.run([py, str(au / "build-og.py"), L.og_key(slug, loc)], check=True)
    rebuild()


if __name__ == "__main__":
    main()
