#!/usr/bin/env python3
"""把最新的 main 合併進目前分支，並自動解決「產物」造成的衝突。

文章列表、上下篇、首頁最新文章、成員數、feed.xml、sitemap.xml 都是腳本產生的，兩個 PR 同時新增文章時
幾乎一定會在這些地方衝突，但真正的內容並沒有衝突。本腳本會：

1. 在乾淨的工作區執行 git fetch origin main，再 git merge --no-commit FETCH_HEAD（已在合併中就沿用）。
2. 逐一處理衝突檔：
   - feed.xml、sitemap.xml：整份是產物，先取 main 的版本，稍後重建。
   - data/articles.json、authoring/og/manifest.json：以 slug 為單位做三方合併（兩邊各自新增或修改不同文章即可自動合併）。
   - HTML：把 <!--lists:…-->、<!--articlenav:…-->、<!--shared:…-->、<!--members:…--> 標記之間的內容先換成佔位符，
     再三方合併其餘內容；其餘內容沒衝突就自動解決，標記內容稍後由腳本重建。
   - 其他檔案或真正的內容衝突：列出來請你手動解決，`git add` 後再執行一次本腳本。
3. 重建 build-shared（必要時）、build-lists、build-feed、build-sitemap，跑 check.py，通過後 commit。之後 git push 即可。

用法：python3 authoring/resolve-generated.py
不會 rebase、不會 force push，也不會 push。
"""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import articles_lib as L  # noqa: E402

ROOT = L.ROOT
WHOLE_FILE = {"feed.xml", "sitemap.xml"}
REGION = re.compile(r"(<!--((?:lists|shared|members):[\w-]+)-->)(.*?)(<!--/\2-->)"
                    r"|(<!--(articlenav):start-->)(.*?)(<!--articlenav:end-->)", re.S)


def git(*args: str, check: bool = True, text: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=text, check=check)


def stage(n: int, path: str) -> str | None:
    """取出衝突檔的某一版：1 = 共同祖先、2 = 目前分支、3 = main；該版不存在時回傳 None。"""
    r = git("show", f":{n}:{path}", check=False)
    return r.stdout if r.returncode == 0 else None


def merge_text(base: str, ours: str, theirs: str) -> tuple[str, bool]:
    with tempfile.TemporaryDirectory() as d:
        files = []
        for name, content in (("ours", ours), ("base", base), ("theirs", theirs)):
            f = Path(d) / name
            f.write_text(content, encoding="utf-8")
            files.append(str(f))
        r = subprocess.run(["git", "merge-file", "-p", *files], capture_output=True, text=True)
    return r.stdout, r.returncode == 0


def mask(text: str) -> tuple[str, dict[str, str]]:
    """把標記之間的產物換成佔位符，回傳（遮蔽後的文字, 佔位符 → 原內容）。"""
    seen: dict[str, int] = {}
    inner: dict[str, str] = {}

    def sub(m: re.Match) -> str:
        start, key, body, end = (m.group(1), m.group(2), m.group(3), m.group(4)) if m.group(1) else \
            (m.group(5), m.group(6), m.group(7), m.group(8))
        n = seen[key] = seen.get(key, 0) + 1
        token = f"@@GENERATED {key} #{n}@@"
        inner[token] = body
        return start + token + end

    return REGION.sub(sub, text), inner


def resolve_html(path: str) -> bool:
    base, ours, theirs = stage(1, path) or "", stage(2, path), stage(3, path)
    if ours is None or theirs is None:
        return False  # 一邊刪除、一邊修改：交給人判斷
    (mb, ib), (mo, io), (mt, it) = mask(base), mask(ours), mask(theirs)
    merged, clean = merge_text(mb, mo, mt)
    if not clean:
        return False
    for token in re.findall(r"@@GENERATED [\w:-]+ #\d+@@", merged):
        merged = merged.replace(token, it.get(token, io.get(token, ib.get(token, ""))), 1)
    (ROOT / path).write_text(merged, encoding="utf-8")
    return True


def merge_keyed(base: dict, ours: dict, theirs: dict) -> dict | None:
    out = {}
    for k in sorted(set(base) | set(ours) | set(theirs)):
        b, o, t = base.get(k), ours.get(k), theirs.get(k)
        if o == t:
            v = o
        elif o == b:
            v = t
        elif t == b:
            v = o
        else:
            return None  # 兩邊改了同一篇
        if v is not None:
            out[k] = v
    return out


def resolve_json(path: str) -> bool:
    try:
        versions = [json.loads(stage(n, path) or ("[]" if path.endswith("articles.json") else "{}")) for n in (1, 2, 3)]
    except json.JSONDecodeError:
        return False
    if path == "data/articles.json":
        merged = merge_keyed(*({a["slug"]: a for a in v} for v in versions))
        if merged is None:
            return False
        L.save_articles(sorted(merged.values(), key=lambda a: (a["date"], a["slug"])))
    else:
        merged = merge_keyed(*versions)
        if merged is None:
            return False
        L.save_manifest(merged)
    return True


def resolve(path: str) -> bool:
    if path in WHOLE_FILE:
        git("checkout", "--theirs", "--", path)
        return True
    if path in ("data/articles.json", "authoring/og/manifest.json"):
        return resolve_json(path)
    if path.endswith(".html"):
        return resolve_html(path)
    return False


def run(script: str, *args: str) -> int:
    return subprocess.run([sys.executable, str(ROOT / "authoring" / script), *args], cwd=ROOT,
                          stdout=subprocess.DEVNULL if script.startswith("build") else None).returncode


def main() -> None:
    if git("rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode != 0:
        if git("branch", "--show-current").stdout.strip() == "main":
            sys.exit("✗ 目前在 main。請在要更新的 PR 分支上執行。")
        if git("status", "--porcelain", "--untracked-files=no").stdout.strip():
            sys.exit("✗ 工作區有未提交的變更，請先 commit 再執行。")
        git("fetch", "-q", "origin", "main")
        r = git("merge", "--no-commit", "--no-ff", "FETCH_HEAD", check=False)
        if "Already up to date" in r.stdout:
            print("✓ 已包含最新的 main，不需要合併。")
            return
        if r.returncode != 0 and "CONFLICT" not in r.stdout:
            sys.exit(f"✗ git merge 失敗：\n{r.stdout}{r.stderr}")

    conflicted = [p for p in git("diff", "--name-only", "--diff-filter=U").stdout.splitlines() if p]
    manual = []
    for p in conflicted:
        if resolve(p):
            git("add", "--", p)
            print(f"已自動解決：{p}")
        else:
            manual.append(p)
    if manual:
        print("\n以下檔案有真正的內容衝突，請手動解決、git add 之後再執行一次本腳本：", file=sys.stderr)
        for p in manual:
            print(f"  {p}", file=sys.stderr)
        sys.exit(1)

    if run("build-shared.py", "--check") != 0:
        run("build-shared.py")
    for script in ("build-lists.py", "build-feed.py", "build-sitemap.py"):
        if run(script) != 0:
            sys.exit(f"✗ {script} 失敗，合併尚未提交。")
    git("add", "-u")
    if run("check.py") != 0:
        sys.exit("✗ check.py 沒通過，合併尚未提交。修正後 git add，再執行一次本腳本。"
                 "（若是文章分享圖過期，執行 python3 authoring/build-og.py --articles）")
    r = git("commit", "--no-edit", check=False)
    if r.returncode != 0:
        sys.exit(f"✗ commit 失敗：\n{r.stdout}{r.stderr}")
    print("✓ 已合併最新的 main 並提交。接著執行 git push 即可。")


if __name__ == "__main__":
    main()
