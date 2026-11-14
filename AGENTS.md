# Agent 工作規範

本檔案是所有 AI coding agent 在本專案工作的共同規範。專案專用入口（例如 `CLAUDE.md`、`GEMINI.md`、`.github/copilot-instructions.md` 與 `.cursor/rules/`）只應引用本檔案，不要各自複製一份會逐漸分歧的規則。

## 專案概況

福爾摩沙自閉大公社（Discord 社群）的官方網站：<https://asdtw.org>。
這是部署在 GitHub Pages 的純靜態 HTML／CSS／少量 JavaScript 專案，`main` 推送後即上線；沒有套件管理、build 系統或測試框架。網站內容與介面文字一律使用繁體中文（`zh-Hant-TW`），語氣認真正式。

## 開始工作前

- 先查看 `git status`，保留使用者已存在的修改，不覆蓋或回退無關變更。
- 先讀 `CONTRIBUTING.md`；若工作涉及文章、行動紀錄、無障礙或 SEO，也要讀其中對應章節。
- 一個變更只處理一件事。除非使用者明確要求，不要 commit、push、開 PR、merge 或修改 GitHub 設定。
- 不要使用外部 CDN、Google Fonts、追蹤碼、Cookie、分析工具或未經說明的第三方資源。

## 常用命令

```bash
python3 -m http.server 8000
python3 authoring/check.py
python3 authoring/build-sitemap.py
python3 authoring/build-lists.py
python3 authoring/build-feed.py
python3 authoring/build-members.py
python3 authoring/md2article.py 原稿.md [--images 資料夾]
python3 authoring/build-og.py
bash authoring/ship.sh "type(scope): 描述"
bash authoring/sync.sh
```

預覽時必須從 repo 根目錄啟動 HTTP server，不能用 `file://`；看到 404 時直接開 `/404.html`。`authoring/check.py` 是唯一的自動檢查，會一次驗證結構、無障礙、連結、色彩對比、SEO、素材、文章衍生檔案與 sitemap。涉及 HTML、CSS、文章或生成檔時，完成後都要執行它。

## 檔案與架構規則

- 主要頁面是 `index.html`、`about.html`、`actions.html`、`accessibility.html`、`articles.html` 與 `404.html`；文章頁在 `articles/`。
- 頁首、頁尾、閱讀設定面板是每頁手寫的靜態 HTML，必須逐字一致；修改共用區塊時同步修改所有根目錄頁與 `articles/*.html`，最後跑檢查。
- 文章的單一來源是 `data/articles.json`；文章頁使用 `authoring/md2article.py` 與 `authoring/article-template.html` 產生，不要手改產出 HTML。列表、上下篇、首頁最新文章、feed、sitemap 由工具重建。
- 所有顏色 token 只放在 `assets/css/style.css` 頂端；深色與高對比的按鈕選擇器及系統 media query 必須同步維護。
- 全部使用 `rem`，禁止 `font-size` 使用 `px`；禁止 `style=`、`<style>`、行內事件與行內 `<script>`。
- 網域以 `CNAME` 為唯一來源。每頁的 canonical、OG／Twitter URL 使用完整的 `https://asdtw.org/...` URL。
- 不要把頁首站名改成圖片。品牌素材與裝飾圖一律 `aria-hidden="true"`；說明性圖片需有非空 `alt`、`width`、`height` 與 `<figcaption>`，且圖中資訊也要出現在正文。
- 首頁主視覺與品牌素材須符合 `check.py` 的 SVG 色票、viewBox、大小及無 text／漸層／濾鏡限制；不要自行替換成不符合品牌規格的圖。

### 行動紀錄與文章

- `actions.html` 的時間軸由新到舊；新增紀錄時同步更新總場次，以及首頁只保留最新三筆的「最近的行動」連結。
- 文章分類固定為「行動記事、社群公告、議題觀點、技術教學」。`draft: true` 的文章不進列表、sitemap 或 feed；範例原稿只供本機預覽，不能提交假文章。
- 改文章標題、分類或分享圖設計後，重跑相應的列表、feed、sitemap 與 `build-og.py`，並提交生成的產物。
- `build-members.py`、`build-lists.py`、`build-feed.py`、`build-sitemap.py` 產生的檔案是衍生檔，修改來源後要重建，不要只手改衍生結果。

## 內容與隱私守則

- 網站不得出現「捍衛全台學權行動」；只描述社群自己的參與。
- 不放現場照片、不列成員名單、不提交成員真名、私人信件、聯絡方式或可辨識的未成年人資訊。
- 說明社群設計時使用重畫的示意圖，不使用站長或成員截圖；圖上不得出現真實成員選擇、頭像或政黨名稱，並標明「示意圖」。
- 不編造日期、人數、經歷、地點或無障礙測試結果。沒有資料就留空或詢問；無障礙聲明不得宣稱認證或實機測試，除非確實完成。
- 保留首頁「左翼立場」卡片中的原生 `<details>` 嘲諷聲明，以及螢幕報讀器提示「（可展開聲明）」；不要移除、改成純文字或藏起來。
- 本群規則原文是：「本群沒有規則，有委屈自己提告去。」管理員保有最終裁量權，不要改寫成其他規則。
- 歡迎措辭採「當事人優先」：歡迎各程度身心障礙者、任何性別與性傾向；健全者與異性戀者可加入，但以當事人需求為優先。
- 創辦人簡介只連到 <https://me.asdtw.org/>，不要另寫其他介紹。
- 中文與英數之間加半形空格，使用全形標點與「」；外部連結須有 `target="_blank" rel="noopener"`，文字註明「（另開新視窗）」。

## 無障礙、SEO 與隱私

- 每頁保留 `lang="zh-Hant-TW"`、跳到主要內容連結、恰好一個 `<main>`、`<nav aria-label>`、恰好一個 `<h1>`、正確標題層級與可見焦點框。
- 互動元件需可用鍵盤操作；變更後在最大字級、高對比與 `prefers-reduced-motion` 下檢查不破版。不要宣稱未做過的 VoiceOver／NVDA 測試。
- 保持頁面 canonical、robots、description、OG／Twitter、favicon、apple-touch-icon 與 JSON-LD 完整；404 必須 `noindex`。
- 每頁（404 除外）保留 View Transitions 的 `<link rel="expect" ...>` 與 `#page-end` 標記；不要破壞 reduced-motion 規則。
- 成員數只能由 `authoring/build-members.py` 靜態更新，禁止訪客端呼叫 Discord API；人數向下取整到十位數。

## 變更流程

1. 從最新 `main` 建立短命分支；分支前綴依 `CONTRIBUTING.md`（如 `content/`、`feat/`、`fix/`、`a11y/`、`docs/`）。
2. 修改後執行相關生成工具與 `python3 authoring/check.py`，必要時用 HTTP server 人工預覽。
3. 檢查 `git diff` 與 `git status`，確認沒有產生不應提交的草稿、敏感資料或無關檔案。
4. Commit 使用約定式格式 `type(scope): 描述`；不要直接在 `main` commit／push，不要 force push 或在 `main` rebase。

`authoring/ship.sh` 會執行 `git add -A`，可能把工作區所有未提交變更帶入 PR；使用前一定要先檢查狀態。品牌原始檔位於 repo 外的 `~/Pictures/福爾摩沙自閉大公社_品牌識別_v1/`，不要把原始素材整包加入 repo。
