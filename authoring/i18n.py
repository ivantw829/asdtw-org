"""多語系（i18n）共用定義。build-shared／build-lists／build-members／build-sitemap／check 都從這裡讀，
語系代碼、站名、分類譯名、日期與人數格式只有這一份。"""

DEFAULT_LOCALE = "zh"
LOCALE_ORDER = ("zh", "en", "ja")
PUBLIC_PAGES = (
    "index.html",
    "about.html",
    "positions.html",
    "actions.html",
    "articles.html",
    "accessibility.html",
)

MONTHS_EN = (
    "",
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)

LOCALES = {
    "zh": {
        "html_lang": "zh-Hant-TW",
        "og_locale": "zh_TW",
        "prefix": "",
        "name": "繁體中文",
        "site_name": "福爾摩沙自閉大公社",
        "lang_nav_label": "語言切換",
        "external_marker": "另開新視窗",
        "og_image_alt": "珊瑚紅底，米白色的站名「福爾摩沙自閉大公社」與英文名 Formosa Autistic Commune，右側是半透明的無限符號標誌",
        "categories": {
            "社群公告": "社群公告",
            "議題觀點": "議題觀點",
            "技術教學": "技術教學",
            "行動記事": "行動記事",
        },
        "empty_category": "這個分類還沒有文章。",
        "empty_latest": "還沒有文章，敬請期待。",
        "tags_label": "標籤：",
        "skip_link": "跳到主要內容",
        "article": {
            "label": "文章", "toc": "本文目錄", "sources": "參考資料", "by": "作者：", "updated": "更新於 ",
            "category": "分類：", "tags": "；標籤：", "action": "相關行動：", "nav": "上一篇與下一篇",
            "prev": "上一篇", "next": "下一篇", "all": "回到文章列表", "home": "首頁",
            "table": "表格", "scroll": "（可左右捲動）", "feed": "福爾摩沙自閉大公社｜文章",
            "draft": "這是草稿，尚未公開：不會出現在文章列表、網站地圖與訂閱源，也不會被搜尋引擎收錄。",
            "translation_note": "",
        },
    },
    "en": {
        "html_lang": "en",
        "og_locale": "en_US",
        "prefix": "/en",
        "name": "English",
        "site_name": "Formosa Autistic Commune",
        "lang_nav_label": "Language",
        "external_marker": "opens in a new tab",
        "og_image_alt": "Coral-red background with off-white title '福爾摩沙自閉大公社' and 'Formosa Autistic Commune', and a translucent infinity symbol mark on the right",
        "categories": {
            "社群公告": "Announcements",
            "議題觀點": "Perspectives",
            "技術教學": "Tutorials",
            "行動記事": "Action Reports",
        },
        "empty_category": "No articles in this category yet.",
        "empty_latest": "No articles yet. Stay tuned.",
        "tags_label": "Tags: ",
        "skip_link": "Skip to main content",
        "article": {
            "label": "Article", "toc": "Contents", "sources": "References", "by": "By ", "updated": "Updated ",
            "category": "Category: ", "tags": "; tags: ", "action": "Related action: ", "nav": "Previous and next articles",
            "prev": "Previous", "next": "Next", "all": "Back to all articles", "home": "Home",
            "table": "Table", "scroll": " (scrolls horizontally)", "feed": "Formosa Autistic Commune | Articles",
            "draft": "This is an unpublished draft: it is not listed, not in the sitemap or feed, and not indexed by search engines.",
            "translation_note": 'This is a translation of an article originally written in Traditional Chinese. If the two differ, the <a href="{href}" lang="zh-Hant-TW" hreflang="zh-Hant-TW">中文原文</a> (Chinese original) prevails.',
        },
    },
    "ja": {
        "html_lang": "ja",
        "og_locale": "ja_JP",
        "prefix": "/ja",
        "name": "日本語",
        "site_name": "フォルモサ自閉大公社",
        "lang_nav_label": "言語切り替え",
        "external_marker": "新しいタブで開きます",
        "og_image_alt": "コーラルレッドの背景に、オフホワイトのサイト名「福爾摩沙自閉大公社」と英語名 Formosa Autistic Commune、右側に半透明の無限記号マーク",
        "categories": {
            "社群公告": "お知らせ",
            "議題觀點": "視点・論考",
            "技術教學": "技術ガイド",
            "行動記事": "活動レポート",
        },
        "empty_category": "このカテゴリにはまだ記事がありません。",
        "empty_latest": "記事はまだありません。今後の公開をお待ちください。",
        "tags_label": "タグ：",
        "skip_link": "メインコンテンツへ移動",
        "article": {
            "label": "記事", "toc": "目次", "sources": "参考資料", "by": "著者：", "updated": "更新：",
            "category": "カテゴリ：", "tags": "；タグ：", "action": "関連する活動：", "nav": "前後の記事",
            "prev": "前の記事", "next": "次の記事", "all": "記事一覧に戻る", "home": "ホーム",
            "table": "表", "scroll": "（横にスクロールできます）", "feed": "フォルモサ自閉大公社｜記事",
            "draft": "これは未公開の下書きです。記事一覧、サイトマップ、フィードには載らず、検索エンジンにも登録されません。",
            "translation_note": 'この記事は繁体字中国語の原文を翻訳したものです。内容に相違がある場合は<a href="{href}" lang="zh-Hant-TW" hreflang="zh-Hant-TW">中文原文</a>（原文）が優先されます。',
        },
    },
}


def locale_of(rel: str) -> str:
    """依相對路徑（如 'index.html'、'en/about.html'、'articles/foo.html'）判斷語系代碼。"""
    for code in ("en", "ja"):
        if rel.startswith(f"{code}/"):
            return code
    return DEFAULT_LOCALE


def base_page(rel: str) -> str:
    """去掉語系前綴的檔名（'en/about.html' → 'about.html'）。"""
    for code in ("en", "ja"):
        if rel.startswith(f"{code}/"):
            return rel[len(code) + 1:]
    return rel


def article_locales(slug: str) -> tuple[str, ...]:
    """這篇文章有哪些語系版本（依 data/articles.json：原文＋translations；依 LOCALE_ORDER 排序）。"""
    import articles_lib as L  # 延後匯入，避免與 articles_lib 互相匯入
    a = next((x for x in L.load_articles() if x.get("slug") == slug), None)
    if a is None or L.is_external(a):
        return ()
    have = {DEFAULT_LOCALE, *L.translations(a)}
    return tuple(c for c in LOCALE_ORDER if c in have)


def is_localized_public(rel: str) -> bool:
    """是否為三語對應的公開頁面。"""
    if rel.startswith("articles/"):
        return False
    return base_page(rel) in PUBLIC_PAGES


def page_href(locale: str, page: str) -> str:
    prefix = LOCALES[locale]["prefix"]
    if page == "index.html":
        return f"{prefix}/"
    return f"{prefix}/{page}"


def page_url(base: str, locale: str, page: str) -> str:
    return f"{base}{page_href(locale, page)}"


def canonical_url(base: str, rel: str) -> str:
    if rel == "index.html":
        return f"{base}/"
    if rel.endswith("/index.html"):
        return f"{base}/{rel[:-len('index.html')]}"
    return f"{base}/{rel}"


def lang_switch_target(rel: str, target_locale: str) -> str:
    """計算從 rel 切換到 target_locale 時的目標連結。"""
    if rel == "404.html":
        return page_href(target_locale, "index.html")
    bp = base_page(rel)
    if bp.startswith("articles/"):
        # 文章頁：目標語系有這篇（原文或譯文）就連過去，否則到該語系的文章列表
        slug = bp[len("articles/"):-len(".html")]
        if target_locale in article_locales(slug):
            return page_href(target_locale, bp)
        return page_href(target_locale, "articles.html")
    return page_href(target_locale, base_page(rel))


def render_lang_switch(rel: str) -> str:
    """產生頂部工具列右側的語言切換 <nav>（無 JS 可用）。"""
    cur = locale_of(rel)
    label = LOCALES[cur]["lang_nav_label"]
    items = []
    for code in LOCALE_ORDER:
        info = LOCALES[code]
        href = lang_switch_target(rel, code)
        attr = ' aria-current="true"' if code == cur else ""
        items.append(
            f'        <li><a href="{href}" lang="{info["html_lang"]}" hreflang="{info["html_lang"]}"{attr}>{info["name"]}</a></li>'
        )
    return (
        f'    <nav class="lang-switch" aria-label="{label}">\n'
        f'      <ul>\n'
        + "\n".join(items)
        + "\n      </ul>\n"
        f'    </nav>'
    )


def fmt_date(iso: str, locale: str = DEFAULT_LOCALE) -> str:
    y, m, d = iso.split("-")
    mi, di = int(m), int(d)
    if locale == "en":
        return f"{MONTHS_EN[mi]} {di}, {y}"
    if locale == "ja":  # 日文排版慣例：數字與漢字之間不加空格
        return f"{y}年{mi}月{di}日"
    return f"{y} 年 {mi} 月 {di} 日"


def fmt_reading_time(minutes: int, locale: str = DEFAULT_LOCALE) -> str:
    if locale == "en":
        return f"~{minutes} min read"
    if locale == "ja":
        return f"約{minutes}分で読めます"
    return f"閱讀約 {minutes} 分鐘"


def fmt_external_suffix(locale: str = DEFAULT_LOCALE) -> str:
    marker = LOCALES[locale]["external_marker"]
    if locale == "en":
        return f" ({marker})"
    return f"（{marker}）"


def fmt_cat_count(name: str, count: int, locale: str = DEFAULT_LOCALE) -> str:
    display = LOCALES[locale]["categories"][name]
    if locale == "en":
        return f"{display} ({count})"
    if locale == "ja":
        return f"{display}（{count}件）"
    return f"{display}（{count} 篇）"


def fmt_member_count(n: int, locale: str = DEFAULT_LOCALE) -> str:
    if locale == "en":
        return f"over {n}"
    if locale == "ja":
        return f"{n}名以上"
    return f"逾 {n} 位"


def fmt_member_date(year: int, month: int, locale: str = DEFAULT_LOCALE) -> str:
    if locale == "en":
        return f"{MONTHS_EN[month]} {year}"
    if locale == "ja":
        return f"{year}年{month}月"
    return f"{year} 年 {month} 月"
