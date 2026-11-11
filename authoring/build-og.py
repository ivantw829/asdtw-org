#!/usr/bin/env python3
"""產生社群分享圖。使用本機 Chrome 無頭截圖 + macOS sips，只用標準函式庫。

輸出：
  assets/img/og.jpg   1200×630 社群分享圖（所有頁共用）
網站圖示（favicon.svg／favicon.ico／apple-touch-icon.png）來自品牌識別交件，不由此腳本產生。

改了站名、標語或卡片設計後執行：python3 authoring/build-og.py
CI 沒有 Chrome，所以產物要一併提交。環境變數 CHROME 可指定瀏覽器路徑。
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
OG = ROOT / "authoring" / "og"


def find_chrome() -> str:
    for c in (os.environ.get("CHROME"),
              "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chrome")):
        if c and pathlib.Path(c).exists():
            return c
    sys.exit("找不到 Chrome。請安裝 Google Chrome，或用 CHROME=/path/to/chrome 指定。")


def shot(page: pathlib.Path, w: int, h: int, out: pathlib.Path, fmt: str) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        png = pathlib.Path(tmp) / "shot.png"
        subprocess.run([find_chrome(), "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--force-device-scale-factor=1", f"--window-size={w},{h}",
                        "--virtual-time-budget=15000", f"--screenshot={png}", page.as_uri()],
                       check=True, capture_output=True, timeout=90)
        if fmt == "jpeg":
            subprocess.run(["sips", "-s", "format", "jpeg", "-s", "formatOptions", "88", str(png), "--out", str(out)],
                           check=True, capture_output=True)
        else:
            shutil.copy(png, out)
    if ROOT in out.parents:
        print(f"  ✓ {out.relative_to(ROOT)}")


def main() -> None:
    shot(OG / "card.html", 1200, 630, ROOT / "assets/img/og.jpg", "jpeg")


if __name__ == "__main__":
    main()
