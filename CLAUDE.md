# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

給 Claude Code 的專案指引。

福爾摩沙自閉大公社（Discord 社群）的網站，https://asdtw.org，純靜態 HTML／CSS／JS，部署在 GitHub Pages（repo：`ivantw829/asdtw-org`，`main` 推上去即上線）。沒有 build 步驟、套件管理或測試框架。內容與介面文字一律繁體中文（zh-Hant-TW），語氣認真正式。

## Commands

```bash
python3 -m http.server 8000        # 本機預覽（頁面用 `/` 開頭的絕對路徑，必須從根目錄服務，不能開 file://）。看 404 請直接開 /404.html，伺服器自己的 404 頁不是網站的
python3 authoring/check.py         # 唯一的「測試」：結構、無障礙、連結、色票對比、sitemap。CI 與 pre-commit 都會跑；沒有「只跑單一項」的選項，錯誤會一次全列出
python3 authoring/build-sitemap.py # 重建 sitemap.xml（含文章、排除 noindex；pre-commit 會自動做並 stage）
python3 authoring/md2article.py 原稿.md [--images 資料夾]  # Markdown → 文章頁，並登錄 JSON、轉 webp、產分享圖、更新列表／feed／sitemap、跑 check（格式見 authoring/article-sample.md）
python3 authoring/build-lists.py   # 把文章列表、上下篇（與上線後首頁「最新文章」）靜態寫進 HTML（pre-commit 自動）
python3 authoring/build-feed.py    # 重建 Atom 訂閱源 feed.xml（pre-commit 自動）
bash authoring/ship.sh "type(scope): 描述"  # 一鍵：分支→commit→push→PR→等 CI→squash merge→同步（CO_AUTHOR、PR_BODY 環境變數可選）
bash authoring/sync.sh             # 本機與 GitHub 對齊
python3 authoring/build-og.py      # 重產分享圖 og.jpg＋過期的文章分享圖（需 Chrome 與 macOS sips；CI 沒有，產物要一併提交）；--articles 只補文章圖、<slug> 只產該篇
```

## 架構

- 四個頁面：`index.html`、`about.html`（關於與加入須知）、`actions.html`（行動紀錄）、`accessibility.html`（無障礙與聯絡、隱私）；外加 `404.html`（noindex，不進 sitemap），以及文章欄位 `articles.html`＋`articles/`（見下方「文章」）。
- **頁首、頁尾、閱讀設定面板是每頁手寫的靜態 HTML，必須逐字相同**（頁首只有 `aria-current="page"` 不同）。這是為了不依賴 JS 就能被螢幕報讀器完整讀取。改其中任何一處，要同步改全部頁面，`check.py` 會驗證。
- 閱讀設定（字級 1–4、配色 default／dark／high）：`assets/js/prefs.js` 在 `<head>` 同步載入，把偏好寫到 `<html data-text data-theme>`，存 `localStorage`；面板（`<details>` 預設收合）預設 `hidden`，有 JS 才顯示。使用者沒手動選時，系統 `prefers-contrast: more` → 高對比、`prefers-color-scheme: dark` → 深色。
- **視覺風格沿用 me.asdtw.org**（奶白紙張、琥珀黃、青綠、墨黑名字標籤、襯線標題、膠囊導覽），但灰字與琥珀褐文字色已加深到 AAA，**不要換回個人站的原色票**。字體只用系統字體，不載入 Google Fonts（隱私）。首頁主視覺 `.hero-art` 是設計師交付的三個 SVG（`assets/img/hero-light/dark/high.svg`，珊瑚紅＋炭灰＋琥珀黃；深色版炭灰換米白；高對比版只有白與黃），以 CSS 背景圖依配色載入，元素 `aria-hidden`；字級調到「特大」以上時隱藏。換圖須符合 `check.py` 第 6 節規格（色票、viewBox `0 0 600 800`、<50KB、無 text／漸層／濾鏡）。
- **品牌素材**（來自品牌識別交件，放 `assets/img/brand/`）：`lockup-dark.svg`／`lockup-light.svg`（橫式組合，頁尾與 404 以背景圖載入，淺色用 dark、深色與高對比用 light）、`lockup-rainbow.svg`（彩虹馬卡龍橫式組合，淺色配色用自帶炭灰底的版本、深色與高對比用 `lockup-rainbow-clear.svg`（去背淺字，淺底看不見），**只能放在 `.badge-pride` 內**，目前僅用於行動紀錄頁）。分享圖由 `authoring/og/banner-coral.svg` 經 `card.html` 產生。以上裝飾元素一律 `aria-hidden="true"`；**頁首站名維持真文字**，不要改成圖片。`check.py` 第 7 節會驗證這些素材（不得含 text／漸層／濾鏡等、色票限制）。
- **色票只有 `assets/css/style.css` 頂端的 token**。深色與高對比各有兩份（`[data-theme=…]` 按鈕版與 media query 系統版），改色必須兩處一起改；`check.py` 會算五組色票的 WCAG 對比，文字低於 7:1 或元件低於 3:1 即失敗。互動元件外框用 `--border`，`--line` 只用於裝飾。
- 全部使用 rem；不得用 px 的 font-size。沒有 `style=`、`<style>`、行內 `<script>`，也不載入任何外部資源（字體用系統字體）。
- **Meta／SEO**：每頁 `<head>` 有 canonical、robots、OG／Twitter（`summary_large_image`，根目錄頁的圖固定為 `/assets/img/og.jpg` 1200×630，文章頁用各自的 `/assets/img/og/<slug>.jpg`）、icon 與 JSON-LD（首頁 Organization＋WebSite，內頁 BreadcrumbList；刻意不放 Event，因為沒有街道地址）。`check.py` 全部會驗證。**改站名、標語或卡片設計（`authoring/og/card.html`）後要執行 `build-og.py`**；網站圖示（`assets/img/favicon.svg`、`apple-touch-icon.png`、根目錄 `favicon.ico`）來自品牌識別交件（左閉右開的無限符號，珊瑚紅底），不由腳本產生；`favicon.ico` 必須含 16／32／48 三種尺寸、另有 `icon-192.png`（Google 搜尋結果要求圖示邊長為 48 的倍數）；這兩個由品牌包的 `標誌-含底色` PNG 縮製。換圖示時這些檔案一起換。JSON-LD 不得出現所屬團體名稱或舊信箱。
- 網域以 `CNAME` 為唯一來源；每頁的 canonical／og:url 是寫死的完整網址，`check.py` 會比對。
- **切頁轉場**（CSS 跨頁 View Transitions：頁首固定、導覽黃色膠囊 `nav-pill` 滑動、內容淡入）：每頁（404 除外）`<head>` 要有 `<link rel="expect" href="#page-end" blocking="render">`，`</footer>` 後要有 `<span id="page-end" hidden></span>`，否則切換會閃空白；`prefers-reduced-motion` 時整個轉場關閉。`check.py` 會驗證。
- **行動紀錄**：`actions.html` 的時間軸由新到舊手寫，每筆有 `id`（如 `tywd-2026`）、標籤（線下聚會、技術支援等）與標題上方的「共 N 場」；新增一筆時要同步改「共 N 場」，並更新首頁 `index.html`「最近的行動」（固定列最新三筆，連到 `actions.html#<id>`，舊的移出首頁）。地點等沒提供的資訊不要寫。
- **頁面都是手寫 HTML，沒有樣板引擎**（例外：文章頁由 `md2article.py` 產生，見下方「文章」）。改共用區塊（頁首、頁尾、`<head>` 的 meta）要對根目錄所有 HTML 與 `articles/*.html` 做同樣的修改，建議用一段 Python／sed 腳本批次取代再跑 `check.py`，不要逐檔手改；不要憑記憶「重新產生」頁面，會蓋掉站長直接在 HTML 裡做的文案修改。
- 新增頁面要同步：複製既有頁面的 `<head>` 與共用區塊 → 所有頁面的導覽加一項 → `build-sitemap.py` 重跑。
- **文章（參考 me.asdtw.org，改成完全靜態）**：`data/articles.json` 是單一來源；`articles/<slug>.html` 由 `authoring/md2article.py` 套 `authoring/article-template.html` 產生，閱讀設定／頁首／頁尾在產生時從 `index.html` 逐字複製（去掉 aria-current）。分類、日期格式、共用區塊擷取、分享圖雜湊都在 `authoring/articles_lib.py`，改分類只改那裡。分類固定四類：行動記事、社群公告、議題觀點、技術教學；`author` 選填（可用筆名，沒填即社群名義，JSON-LD 為 Organization）；`action` 選填，連到 `actions.html#<id>`；`draft: true` 為 noindex 且不進列表／sitemap／feed。列表（`articles.html` 依分類分區）、上下篇、首頁最新文章都由 `build-lists.py` 寫在 `<!--lists:…-->`／`<!--articlenav:…-->` 標記之間，不依賴 JS；沒有留言、18+ 閘門與標籤篩選（都需要 JS 或外部資源）。每篇分享圖 `assets/img/og/<slug>.jpg` 由 `authoring/og/article-card.html` 產生，`authoring/og/manifest.json` 記錄輸入雜湊，`check.py` 以此判斷過期。`check.py` 第 9 節驗證 JSON ⇄ HTML 逐字一致、分享圖、列表與 feed 是否最新。`authoring/article-sample.md` 是範例原稿（`draft: true`）。
- **文章欄位已公開**：導覽在「行動紀錄」後有「文章」；`check.py` 要求「`articles.html` 公開（index）⇔ 導覽有『文章』」。首頁「最新文章」區塊的 `<!--lists:latest-->` 標記由 `build-lists.py` 填入最新三篇（沒有文章時顯示「還沒有文章，敬請期待。」），不要手改。範例原稿 `authoring/article-sample.md` 只在本機產生來看版型，看完要刪掉產出的 `articles/sample-article.html` 與 JSON 那一筆，不要提交假文章。
- 品牌素材（標誌、圖示、主視覺）的原始檔在 repo 之外：`~/Pictures/福爾摩沙自閉大公社_品牌識別_v1/`（內含設計規格書，色票與使用規範以它為準）。

## 內容守則（來自站長的明確決定）

- **網站上不得出現「捍衛全台學權行動」**（社群所屬團體）；活動只寫社群自己的參與。
- **不放照片、不列成員名單**；站長也不打算放照片。
- 說明社群設計（如身分組）時，**用重畫的示意圖，不用站長或成員的截圖**；示意圖不得出現真實成員的選擇、頭像或政黨名稱，並標明「示意圖」。目前只有 `assets/img/roles-mock.svg`（關於頁），`check.py` 第 8 節會驗證；說明性圖片必須有非空 alt、width／height 與 `<figcaption>`，圖中資訊在正文要有同樣內容的文字。
- 首頁「左翼立場」卡片裡那句關於疫苗的話是站長刻意做的嘲諷（反疫苗陰謀論），藏在原生 `<details class="aside">` 裡，點開才看到「以上是對反疫苗陰謀論的嘲諷。疫苗不會導致自閉症。」。**不要移除聲明、不要改成純文字或隱藏連結**；`<summary>` 內的 `visually-hidden`「（可展開聲明）」是給螢幕報讀器的提示，要保留。
- 不要編造事實（日期、人數、經歷、無障礙測試結果）。沒有提供就留空或詢問。無障礙聲明不得宣稱已通過認證或實機測試，除非真的做過。
- 本群唯一規則原文：「本群沒有規則，有委屈自己提告去。」說明為管理員保有最終裁量權，不要改寫成其他規則。
- 歡迎對象措辭為「當事人優先」：歡迎各程度身心障礙者、任何性別與性傾向；健全者與異性戀者可加入但以當事人需求為優先。不要寫成「不歡迎」。
- 創辦人簡介只連到 https://me.asdtw.org/，不另寫。
- 排版：全形標點，中文與英數之間加半形空格，引號用「」；外部連結 `target="_blank" rel="noopener"` 且文字註明「（另開新視窗）」。

## 工作流程（完整版見 CONTRIBUTING.md）

- `main` 受保護：只能經 PR、CI（`check`、`pr-title`）通過後 squash merge。PR 標題即 `main` 的 commit 訊息，必須是約定式 commit：`type(scope): 描述`；分支前綴對應 type。
- 本機 hooks 在 `.githooks/`，每個 clone 要自己啟用：`git config core.hooksPath .githooks`。pre-commit 拒絕在 `main` 提交、更新 sitemap、跑 `check.py`；pre-push 拒絕推 `main`。
- **`ship.sh` 會 `git add -A`，把工作區所有未提交的變更都帶進這個 PR**（包含站長直接改的文案）。發布前先 `git status`，確認內容都是要一起發布的；站長可能在另一個流程已經合併過同樣的變更，這時 `ship.sh` 會回報「沒有任何變更可以發布」，並留下一個空分支，用 `git switch main && git branch -d <分支>` 清掉即可。
- 一個 PR 做一件事。不要 force push、不要在 `main` 上 rebase。
- `.claude/`（含預覽用的 `launch.json`）已被 `.gitignore` 排除，不會進 repo。
- 沒有被要求就不要 commit、push 或開 PR。
