#!/usr/bin/env python3
"""從本機向 Discord 取得成員數，靜態寫進 HTML（訪客端不連外、不需要 JS）。改寫的區塊：

  index.html、about.html   <!--members:count--> … <!--/members:count-->   如「逾 400 位」
  about.html               <!--members:date--> … <!--/members:date-->     如「2026 年 11 月」（人數有變才更新）

人數取自首頁「加入 Discord 社群」按鈕的邀請碼，往下取整到十位數（409 → 逾 400）。
連不上 Discord 時只印警告、不改檔案，不會擋下提交。pre-commit 會自動執行；會印出被改寫的檔案。
用法：python3 authoring/build-members.py
"""
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = [ROOT / "index.html", ROOT / "about.html"]


def warn(msg: str) -> None:
    print(f"! 成員數未更新：{msg}", file=sys.stderr)


def invite_code() -> str | None:
    m = re.search(r'href="https://discord\.gg/([A-Za-z0-9-]+)"', (ROOT / "index.html").read_text(encoding="utf-8"))
    return m.group(1) if m else None


def fetch_count(code: str) -> int:
    req = urllib.request.Request(f"https://discord.com/api/v10/invites/{code}?with_counts=true",
                                 headers={"User-Agent": "site-build-script"})
    with urllib.request.urlopen(req, timeout=8) as res:
        return int(json.load(res)["approximate_member_count"])


def label(n: int) -> str:
    # 「逾」是「超過」，剛好整十時要往下一級（400 → 逾 390）
    return f"逾 {(n - 1) // 10 * 10} 位"


def sub(text: str, key: str, inner: str) -> tuple[str, bool]:
    pat = re.compile(rf"(<!--members:{key}-->)(.*?)(<!--/members:{key}-->)", re.S)
    return pat.subn(lambda m: m.group(1) + inner + m.group(3), text)[0], bool(pat.search(text))


def main() -> None:
    code = invite_code()
    if not code:
        return warn("index.html 找不到 discord.gg 邀請連結")
    try:
        n = fetch_count(code)
    except Exception as exc:  # 離線、限流、API 改版都一樣：保留現有數字
        return warn(f"無法取得 Discord 人數（{exc}）")
    count = label(n)
    today = datetime.date.today()
    date = f"{today.year} 年 {today.month} 月"
    for f in FILES:
        old = f.read_text(encoding="utf-8")
        m = re.search(r"<!--members:count-->(.*?)<!--/members:count-->", old, re.S)
        if not m:
            warn(f"{f.name} 找不到 <!--members:count--> 標記")
            continue
        if m.group(1) == count:
            continue
        new, _ = sub(old, "count", count)
        new, _ = sub(new, "date", date)
        f.write_text(new, encoding="utf-8")
        print(f.relative_to(ROOT))


if __name__ == "__main__":
    main()
