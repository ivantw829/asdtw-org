#!/usr/bin/env python3
"""依 CNAME 與根目錄的 HTML 頁面產生 sitemap.xml（404 不收錄）。pre-commit 會自動執行。"""
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
domain = (ROOT / "CNAME").read_text().strip()
pages = sorted(p for p in ROOT.glob("*.html") if p.name != "404.html")


def lastmod(p: Path) -> str:
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%cs", "--", p.name],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()
        if out:
            return out
    except Exception:
        pass
    return date.today().isoformat()


def loc(p: Path) -> str:
    return f"https://{domain}/" if p.name == "index.html" else f"https://{domain}/{p.name}"


order = sorted(pages, key=lambda p: (p.name != "index.html", p.name))
lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
for p in order:
    lines += ["  <url>", f"    <loc>{loc(p)}</loc>", f"    <lastmod>{lastmod(p)}</lastmod>", "  </url>"]
lines.append("</urlset>")
(ROOT / "sitemap.xml").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"sitemap.xml：{len(order)} 頁")
