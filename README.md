# 福爾摩沙自閉大公社

Discord 社群「福爾摩沙自閉大公社」的官方網站：<https://asdtw.org>

純靜態 HTML／CSS／少量 JavaScript，部署在 GitHub Pages。沒有 build 步驟，也沒有套件管理。

## 快速開始

```bash
git clone https://github.com/ivantw829/asdtw-org.git && cd asdtw-org
git config core.hooksPath .githooks && git config commit.template .gitmessage
python3 -m http.server 8000     # 開啟 http://localhost:8000
python3 authoring/check.py      # 品質與無障礙檢查（CI 也會跑）
```

## 結構

| 路徑 | 說明 |
|---|---|
| `index.html` `about.html` `actions.html` `accessibility.html` | 四個頁面，共用頁首／頁尾／閱讀設定須逐字相同 |
| `assets/css/style.css` | 唯一的樣式表，含色票 token、字級與高對比 |
| `assets/js/prefs.js` | 閱讀設定（字級、對比），只用 `localStorage` |
| `authoring/` | 檢查與工具：`check.py`、`build-sitemap.py`、`ship.sh`、`sync.sh`、`setup-github.sh` |

協作規範請見 [CONTRIBUTING.md](CONTRIBUTING.md)；與 Claude Code 協作請見 [CLAUDE.md](CLAUDE.md)。
