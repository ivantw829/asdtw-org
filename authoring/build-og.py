#!/usr/bin/env python3
"""產生社群分享圖。使用本機 Chrome 無頭截圖 + macOS sips，只用標準函式庫。

輸出：
  assets/img/og.jpg            1200×630 全站分享圖（根目錄各頁共用，來源 authoring/og/card.html）
  assets/img/og/<slug>.jpg     每篇文章的分享圖（來源 authoring/og/article-card.html，標題與分類取自 data/articles.json）
  assets/img/og/<語系>/<slug>.jpg  英／日文譯文的分享圖（來源 authoring/og/article-card-i18n.html）
網站圖示（favicon.svg／favicon.ico／apple-touch-icon.png）來自品牌識別交件，不由此腳本產生。

用法：
  python3 authoring/build-og.py              全站圖＋補缺少或過期的文章圖（改了站名、標語或 card.html 後執行）
  python3 authoring/build-og.py --articles   只補缺少或過期的文章圖（pre-commit 用）
  python3 authoring/build-og.py --all        全站圖＋全部文章圖重產
  python3 authoring/build-og.py <slug>…      只重產指定文章（譯文寫成 en/<slug>、ja/<slug>）
文章圖是否過期由 authoring/og/manifest.json 的輸入雜湊判斷（標題、分類、卡片範本、標誌）。
CI 沒有 Chrome，所以產物要一併提交。環境變數 CHROME 可指定瀏覽器路徑。
"""
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402
import i18n as I  # noqa: E402

ROOT = L.ROOT
OG = ROOT / "authoring" / "og"


def find_chrome() -> str:
    for c in (os.environ.get("CHROME"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and Path(c).exists():
            return c
    sys.exit("找不到 Chrome。請安裝 Google Chrome，或用 CHROME=/path/to/chrome 指定。")


def shot(url: str, w: int, h: int, out: Path, fmt: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = Path(tmp) / "shot.png"
        subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={w},{h}",
                        "--virtual-time-budget=15000", f"--screenshot={png}", url],
                       check=True, capture_output=True, timeout=90)
        if fmt == "jpeg":
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88", str(png), "--out", str(out)],
                           check=True, capture_output=True)
        else:
            shutil.copy(png, out)
    if ROOT in out.parents:
        print(f"  ✓ {out.relative_to(ROOT)}")


def article_card(a: dict, locale: str) -> None:
    if locale == L.DEFAULT_LOCALE:
        url = L.OG_CARD.as_uri() + "?" + urllib.parse.urlencode({"title": a["title"], "category": a["category"]})
    else:
        info = I.LOCALES[locale]
        url = L.OG_CARD_I18N.as_uri() + "?" + urllib.parse.urlencode({
            "title": a["title"], "category": info["categories"][a["category"]],
            "label": info["article"]["label"], "lang": info["html_lang"]})
    shot(url, 1200, 630, L.og_file(a["slug"], locale), "jpeg")


def cards() -> dict[str, tuple[dict, str]]:
    """{manifest 鍵: (該語系的文章欄位, 語系)}：每篇站內文章的原文與各譯文。"""
    out = {}
    for a in L.load_articles():
        if L.is_external(a):
            continue
        for loc in (L.DEFAULT_LOCALE, *L.translations(a)):
            out[L.og_key(a["slug"], loc)] = (L.localized(a, loc), loc)
    return out


def articles(only: list[str] | None, force: bool) -> None:
    data = cards()
    manifest = L.load_manifest()
    for key in only or []:
        if key not in data:
            sys.exit(f"data/articles.json 沒有 {key}")
    for key, (a, loc) in data.items():
        if only is not None and key not in only:
            continue
        h = L.og_hash(a, loc)
        if force or only is not None or manifest.get(key) != h or not L.og_file(a["slug"], loc).exists():
            article_card(a, loc)
            manifest[key] = h
    # 清掉已刪除文章（或譯文）的圖與紀錄
    for key in [k for k in manifest if k not in data]:
        del manifest[key]
    for f in sorted(L.OG_DIR.rglob("*.jpg")) if L.OG_DIR.exists() else []:
        if f.relative_to(L.OG_DIR).with_suffix("").as_posix() not in data:
            f.unlink()
            print(f"  − 移除 {f.relative_to(ROOT)}")
    L.save_manifest(manifest)


def main() -> None:
    args = sys.argv[1:]
    if "--articles" in args:
        articles(None, False)
    elif "--all" in args:
        shot((OG / "card.html").as_uri(), 1200, 630, ROOT / "assets/img/og.jpg", "jpeg")
        articles(None, True)
    elif args:
        articles(args, True)
    else:
        shot((OG / "card.html").as_uri(), 1200, 630, ROOT / "assets/img/og.jpg", "jpeg")
        articles(None, False)


if __name__ == "__main__":
    main()
