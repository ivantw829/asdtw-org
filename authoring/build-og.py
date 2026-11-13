#!/usr/bin/env python3
"""產生社群分享圖。使用本機 Chrome 無頭截圖 + macOS sips，只用標準函式庫。

輸出：
  assets/img/og.jpg            1200×630 全站分享圖（根目錄各頁共用，來源 authoring/og/card.html）
  assets/img/og/<slug>.jpg     每篇文章的分享圖（來源 authoring/og/article-card.html，標題與分類取自 data/articles.json）
網站圖示（favicon.svg／favicon.ico／apple-touch-icon.png）來自品牌識別交件，不由此腳本產生。

用法：
  python3 authoring/build-og.py              全站圖＋補缺少或過期的文章圖（改了站名、標語或 card.html 後執行）
  python3 authoring/build-og.py --articles   只補缺少或過期的文章圖（pre-commit 用）
  python3 authoring/build-og.py --all        全站圖＋全部文章圖重產
  python3 authoring/build-og.py <slug>…      只重產指定文章
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


def article_card(a: dict) -> None:
    url = L.OG_CARD.as_uri() + "?" + urllib.parse.urlencode({"title": a["title"], "category": a["category"]})
    shot(url, 1200, 630, L.OG_DIR / f"{a['slug']}.jpg", "jpeg")


def articles(only: list[str] | None, force: bool) -> None:
    data = {a["slug"]: a for a in L.load_articles()}
    manifest = L.load_manifest()
    for slug in only or []:
        if slug not in data:
            sys.exit(f"data/articles.json 沒有 {slug}")
    for slug, a in data.items():
        if only is not None and slug not in only:
            continue
        h = L.og_hash(a)
        if force or only is not None or manifest.get(slug) != h or not (L.OG_DIR / f"{slug}.jpg").exists():
            article_card(a)
            manifest[slug] = h
    # 清掉已刪除文章的圖與紀錄
    for slug in [s for s in manifest if s not in data]:
        del manifest[slug]
    for f in L.OG_DIR.glob("*.jpg") if L.OG_DIR.exists() else []:
        if f.stem not in data:
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
