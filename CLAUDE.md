# CLAUDE.md

給 Claude Code 的專案指引。

福爾摩沙自閉大公社（Discord 社群）的網站，https://asdtw.org，純靜態 HTML／CSS／JS，部署在 GitHub Pages（repo：`ivantw829/asdtw-org`，`main` 推上去即上線）。沒有 build 步驟、套件管理或測試框架。內容與介面文字一律繁體中文（zh-Hant-TW），語氣認真正式。

## Commands

```bash
python3 -m http.server 8000        # 本機預覽
python3 authoring/check.py         # 唯一的「測試」：結構、無障礙、連結、色票對比、sitemap。CI 與 pre-commit 都會跑
python3 authoring/build-sitemap.py # 重建 sitemap.xml（pre-commit 會自動做並 stage）
bash authoring/ship.sh "type(scope): 描述"  # 一鍵：分支→commit→push→PR→等 CI→squash merge→同步（CO_AUTHOR、PR_BODY 環境變數可選）
bash authoring/sync.sh             # 本機與 GitHub 對齊
python3 authoring/build-og.py      # 重產分享圖 og.jpg（需 Chrome 與 macOS sips；CI 沒有，產物要一併提交）
```

## 架構

- 四個頁面：`index.html`、`about.html`（關於與加入須知）、`actions.html`（行動紀錄）、`accessibility.html`（無障礙與聯絡、隱私）；外加 `404.html`（noindex，不進 sitemap）。
- **頁首、頁尾、閱讀設定面板是每頁手寫的靜態 HTML，必須逐字相同**（頁首只有 `aria-current="page"` 不同）。這是為了不依賴 JS 就能被螢幕報讀器完整讀取。改其中任何一處，要同步改全部頁面，`check.py` 會驗證。
- 閱讀設定（字級 1–4、配色 default／dark／high）：`assets/js/prefs.js` 在 `<head>` 同步載入，把偏好寫到 `<html data-text data-theme>`，存 `localStorage`；面板（`<details>` 預設收合）預設 `hidden`，有 JS 才顯示。使用者沒手動選時，系統 `prefers-contrast: more` → 高對比、`prefers-color-scheme: dark` → 深色。
- **視覺風格沿用 me.asdtw.org**（奶白紙張、琥珀黃、青綠、墨黑名字標籤、襯線標題、膠囊導覽），但灰字與琥珀褐文字色已加深到 AAA，**不要換回個人站的原色票**。字體只用系統字體，不載入 Google Fonts（隱私）。首頁主視覺 `.hero-art` 是設計師交付的三個 SVG（`assets/img/hero-light/dark/high.svg`，珊瑚紅＋炭灰＋琥珀黃；深色版炭灰換米白；高對比版只有白與黃），以 CSS 背景圖依配色載入，元素 `aria-hidden`；字級調到「特大」以上時隱藏。換圖須符合 `check.py` 第 6 節規格（色票、viewBox `0 0 600 800`、<50KB、無 text／漸層／濾鏡）。
- **色票只有 `assets/css/style.css` 頂端的 token**。深色與高對比各有兩份（`[data-theme=…]` 按鈕版與 media query 系統版），改色必須兩處一起改；`check.py` 會算五組色票的 WCAG 對比，文字低於 7:1 或元件低於 3:1 即失敗。互動元件外框用 `--border`，`--line` 只用於裝飾。
- 全部使用 rem；不得用 px 的 font-size。沒有 `style=`、`<style>`、行內 `<script>`，也不載入任何外部資源（字體用系統字體）。
- **Meta／SEO**：每頁 `<head>` 有 canonical、robots、OG／Twitter（`summary_large_image`，圖固定為 `/assets/img/og.jpg` 1200×630）、icon 與 JSON-LD（首頁 Organization＋WebSite，內頁 BreadcrumbList；刻意不放 Event，因為沒有街道地址）。`check.py` 全部會驗證。**改站名、標語或卡片設計（`authoring/og/card.html`）後要執行 `build-og.py`**；網站圖示（`assets/img/favicon.svg`、`apple-touch-icon.png`、根目錄 `favicon.ico`）來自品牌識別交件（左閉右開的無限符號，珊瑚紅底），不由腳本產生；換圖示時三個檔案一起換。JSON-LD 不得出現所屬團體名稱或舊信箱。
- 網域以 `CNAME` 為唯一來源；每頁的 canonical／og:url 是寫死的完整網址，`check.py` 會比對。
- 新增頁面要同步：複製既有頁面的 `<head>` 與共用區塊 → 所有頁面的導覽加一項 → `build-sitemap.py` 重跑。

## 內容守則（來自站長的明確決定）

- **網站上不得出現「捍衛全台學權行動」**（社群所屬團體）；活動只寫社群自己的參與。
- **不放照片、不列成員名單**；站長也不打算放照片。
- 不要編造事實（日期、人數、經歷、無障礙測試結果）。沒有提供就留空或詢問。無障礙聲明不得宣稱已通過認證或實機測試，除非真的做過。
- 本群唯一規則原文：「本群沒有規則，有委屈自己提告去。」說明為管理員保有最終裁量權，不要改寫成其他規則。
- 歡迎對象措辭為「當事人優先」：歡迎各程度身心障礙者、任何性別與性傾向；健全者與異性戀者可加入但以當事人需求為優先。不要寫成「不歡迎」。
- 創辦人簡介只連到 https://me.asdtw.org/，不另寫。
- 排版：全形標點，中文與英數之間加半形空格，引號用「」；外部連結 `target="_blank" rel="noopener"` 且文字註明「（另開新視窗）」。

## 工作流程（完整版見 CONTRIBUTING.md）

- `main` 受保護：只能經 PR、CI（`check`、`pr-title`）通過後 squash merge。PR 標題即 `main` 的 commit 訊息，必須是約定式 commit：`type(scope): 描述`；分支前綴對應 type。
- 本機 hooks 在 `.githooks/`，每個 clone 要自己啟用：`git config core.hooksPath .githooks`。pre-commit 拒絕在 `main` 提交、更新 sitemap、跑 `check.py`；pre-push 拒絕推 `main`。
- 一個 PR 做一件事。不要 force push、不要在 `main` 上 rebase。
- 沒有被要求就不要 commit、push 或開 PR。
