# 工作流程

> 這份文件是接手維護的完整指引，不需要用 Claude 也能照著做。`CLAUDE.md` 內容與本檔重疊（給 Claude Code 讀）；**改規則時兩份要同步改**。

採 **trunk-based development**：`main` 永遠可部署（推到 `main` 即自動上線 asdtw.org），所有變更都在短命分支完成，經 PR 與 CI 通過後 squash merge。

## 1. 分支

| 前綴 | 用途 | 範例 |
|---|---|---|
| `content/` | 文字、行動紀錄、文章 | `content/actions-2026-pride` |
| `feat/` | 新功能或新頁面 | `feat/faq-page` |
| `fix/` | 錯誤修正 | `fix/nav-focus-ring` |
| `a11y/` | 無障礙改善（commit type 用 `fix` 或 `feat`，scope 用 `a11y`） | `a11y/larger-touch-targets` |
| `style/` `refactor/` | 外觀、重構（不改行為） | `style/hero-spacing` |
| `docs/` `chore/` `ci/` | 文件、雜項、自動化 | `docs/update-claude-md` |

- 從最新的 `main` 開分支，存活不超過幾天；分支名只用小寫英數與連字號。
- 不直接在 `main` 提交或推送（本機 hook 會擋，GitHub 端也有分支保護）。

## 2. Commit 訊息（約定式 commit）

```
type(scope): 描述
```

- **type**：`feat` `fix` `content` `docs` `style` `refactor` `perf` `chore` `ci` `revert`
- **scope**（選填）：`home` `about` `actions` `articles` `article` `a11y` `design` `seo` `authoring` `ci`
- 描述 72 字內、不加句號；說明「為什麼」比「改了什麼」重要。
- 破壞性變更在 type 後加 `!`。

```
content(actions): 新增 2026 臺灣同志遊行紀錄
fix(a11y): 修正高對比模式下按鈕焦點框不明顯
```

## 3. 日常流程

### 一鍵發布（建議）

```bash
bash authoring/ship.sh "content(actions): 新增某某行動紀錄"
```

開分支 → 檢查 → commit → push → 開 PR → CI 通過後自動 squash merge → 同步本機。**執行後就會直接上線**；只想開 PR 給人審查時請用下面的手動流程。

- `ship.sh` 會 `git add -A`，工作區所有未提交的變更（包含別人直接改的文案）都會一起進這個 PR。執行前先 `git status`，確認都是要一起發布的。
- 如果同樣的變更已經在另一個流程合併過，`ship.sh` 會回報「沒有任何變更可以發布」並留下一個空分支，用 `git switch main && git branch -d <分支>` 清掉即可。

### 手動流程

```bash
git switch main && git pull
git switch -c content/<名稱>
# 修改、預覽（python3 -m http.server 8000）
git add -A && git commit        # hook 會更新 sitemap、跑 check.py、驗證 commit 格式
git push
gh pr create --fill && gh pr merge --auto --squash
bash authoring/sync.sh
```

- **一個 PR 做一件事**。PR 標題就是 `main` 上的 commit 訊息，必須符合約定式 commit。
- 還原用 `git revert` 開 PR，不改歷史；`main` 不得 force push 或 rebase。
- pre-commit 會自動更新成員數與 sitemap 日期（見第 9 節），這些變更會跟著進 commit。提交後用 `git show --stat` 看一下，跟這次工作無關的變更請拆到另一個 PR。

## 4. 新增一場行動紀錄

1. `git switch -c content/<slug>`
2. 在 `actions.html` 的時間軸 `<ol class="timeline">` **最上方**（新到舊）複製一個 `<li>`，改 `id`（如 `tywd-2026`）、標籤（線下聚會、技術支援等）、標題、`<time datetime>` 與說明。**地點等沒有提供的資訊不要寫，也不要自己推測。**
3. 標題上方的「共 N 場」要同步 +1。
4. 首頁 `index.html`「最近的行動」固定列最新 3 場，每筆連到 `actions.html#<id>`；新的放最上面，最舊的那筆移出首頁。
5. `bash authoring/ship.sh "content(actions): 新增〈行動名稱〉紀錄"`

## 4.1 發表文章

文章頁由 Markdown 原稿產生，不要手寫或手改產生的 HTML（重跑會被覆蓋）。

1. 照 `authoring/article-sample.md` 的格式寫原稿（想先看版型，可在本機對它跑 md2article，看完刪掉產出的頁面與 JSON 那一筆，不要提交）（frontmatter：`title`、`slug`、`date`、`category`、`tags`、`summary`、`lead`，選填 `author`、`action`、`updated`、`draft`）。分類只有「行動記事、社群公告、議題觀點、技術教學」；副標籤先看 `data/articles.json` 已有哪些，意思相近就沿用。
2. `python3 authoring/md2article.py 原稿.md --images 圖片資料夾`：產生 `articles/<slug>.html`、登錄 `data/articles.json`、轉 webp、產分享圖（需 Chrome）、更新列表／上下篇／訂閱源／sitemap，最後跑 `check.py`。改稿後重跑同一份原稿即更新。
3. 本機預覽 `/articles/<slug>.html` 與 `/articles.html`，確認後 `bash authoring/ship.sh "content(article): 新增〈標題〉"`。

- 作者可用筆名，沒填就是社群名義；未經本人同意不寫成員的真名。
- 不放現場照片與成員截圖；說明用的圖重畫成示意圖，圖說標明「示意圖」，圖中資訊在正文也要有文字。
- 文章列表、上下篇與首頁「最新文章」都由腳本產生（見第 9 節），不要手改。`articles.html` 公開（index）時導覽必須有「文章」，反之亦然，`check.py` 會驗證。
- 草稿（`draft: true`）不會出現在列表、sitemap 與訂閱源，但知道網址的人看得到，不要放敏感內容。
- 刪除文章：刪掉 `articles/<slug>.html` 與 `data/articles.json` 那一筆，再跑 `python3 authoring/build-og.py --articles`、`build-lists.py`、`build-feed.py`、`build-sitemap.py`。

## 5. 無障礙規範（嚴格實施，CI 強制）

`authoring/check.py` 會擋下以下任一項：

- 頁面缺少 `lang="zh-Hant-TW"`、`<main>`、`<nav aria-label>`、跳到主要內容連結；`<h1>` 不是恰好一個；標題跳級。
- 色票文字對比低於 7:1（AAA），或介面元件低於 3:1；兩份高對比色票不一致。
- `font-size` 使用 px；`style=`、`<style>`、行內事件、行內 `<script>`、外部 CSS／JS。
- `<img>` 沒有 `alt`；`<button>` 沒有 `type`；連結文字空白或只有「點此」「更多」。
- 另開新視窗的連結沒有 `rel="noopener"`，或文字沒註明「另開新視窗」。
- 頁首／頁尾／閱讀設定與 `authoring/partials/` 不一致（只改片段檔，再執行 `python3 authoring/build-shared.py`）；導覽沒有恰好一個 `aria-current="page"`。
- 站內連結或錨點指向不存在的目標；sitemap 缺頁。
- 加入 `<video>` `<audio>` `<iframe>` 等多媒體：必須先補上字幕／文字稿規範與更新 `check.py`。

自動檢查無法取代人工測試。涉及互動的變更，請在 PR 勾選：鍵盤走完整頁、字級最大與高對比下不破版；有條件時用 VoiceOver 或 NVDA 讀過。

## 6. Meta／SEO 規範（CI 強制）

- 每頁需有 canonical、`robots`（404 為 `noindex`）、50～160 字的 description、OG／Twitter 圖（`twitter:card` 為 `summary_large_image`）與 favicon／apple-touch-icon。
- 首頁需有 Organization＋WebSite JSON-LD，內頁需有 BreadcrumbList（最後一項須等於 canonical）。刻意不放 Event（行動沒有街道地址）；JSON-LD 不得出現所屬團體名稱或舊信箱。
- 改站名、標語或分享圖設計後執行 `python3 authoring/build-og.py`（需 Chrome）並提交 `assets/img/` 的產物；`og.jpg` 必須是 1200×630、小於 300KB。
- 文章頁的分享圖是 `assets/img/og/<slug>.jpg`（`authoring/og/article-card.html` 產生），標題或分類改了會被判定過期，`check.py` 會提示重產。

## 7. 隱私與內容守則

以下是站長明確做過的決定，大多數 CI 擋不到，修改文案前請先讀完。

- **不放照片，不列成員名單。** 這是社群的決定，用來保護身心障礙者與性別少數成員；站長也不打算放照片。
- **網站上不得出現「捍衛全台學權行動」**（社群所屬的團體），包括 JSON-LD；活動只寫社群自己的參與。
- **首頁「左翼立場」卡片裡關於疫苗的那句話是刻意的嘲諷**（針對反疫苗陰謀論）。聲明「以上是對反疫苗陰謀論的嘲諷。疫苗不會導致自閉症。」藏在原生 `<details class="aside">` 裡，點開才看得到。不要移除聲明，不要改成純文字或隱藏連結；`<summary>` 內的 `visually-hidden`「（可展開聲明）」是給螢幕報讀器的提示，要保留。
- **群規原文**是「本群沒有規則，有委屈自己提告去。」，說明為管理員保有最終裁量權。不要改寫成其他規則。
- **歡迎對象的措辭是「當事人優先」**：歡迎各種程度的身心障礙者、任何性別與性傾向的人；健全者與異性戀者可以加入，但以當事人的需求為優先。不要寫成「不歡迎」。
- 創辦人簡介只連到 https://me.asdtw.org/，不另外寫。
- **不要編造事實**（日期、人數、經歷、無障礙測試結果）。沒有提供就留空或詢問站長。無障礙聲明不得宣稱已通過認證或實機測試，除非真的做過。
- 說明社群設計（例如身分組）時，用**重畫的示意圖**，不用站長或成員的截圖。示意圖不得出現真實成員的選擇、頭像或政黨名稱，圖說要標明「示意圖」，圖中的資訊在正文也要有同樣內容的文字。目前只有 `assets/img/roles-mock.svg`（關於頁）。
- 排版：全形標點，中文與英數之間加半形空格，引號用「」；語氣認真正式，一律使用繁體中文。
- 不提交：金鑰、私人信件、成員的全名與聯絡方式、可辨識的未成年人資訊。已提交的敏感內容即使刪除仍留在歷史裡，提交前請確認。
- 不使用 Cookie、分析或追蹤碼，不載入外部字體與腳本；若要新增，須先更新「隱私說明」。
- 提交信箱使用 GitHub noreply 位址。

## 8. 設計與品牌

- 視覺沿用 [me.asdtw.org](https://me.asdtw.org/)（奶白紙張、琥珀黃、青綠、襯線標題、膠囊導覽），但灰字與琥珀褐文字色已加深到 AAA 對比，**不要換回個人站的原色票**。字體只用系統字體，不載入 Google Fonts（隱私）。
- **色票只在 `assets/css/style.css` 頂端的 token**。深色與高對比各有兩份（`[data-theme=…]` 按鈕版與 media query 系統版），改色時兩處要一起改。互動元件的外框用 `--border`，`--line` 只用於裝飾。
- 首頁主視覺是設計師交付的三個 SVG（`assets/img/hero-light/dark/high.svg`），依配色以 CSS 背景圖載入，字級調到「特大」以上時隱藏。換圖須符合規格：只用指定色票、viewBox `0 0 600 800`、小於 50KB、不得有 text、漸層或濾鏡（`check.py` 會驗證）。
- 品牌素材在 `assets/img/brand/`：`lockup-dark.svg`／`lockup-light.svg` 用於頁尾與 404（淺色配色用 dark，深色與高對比用 light）。彩虹版 `lockup-rainbow.svg`（淺色用）與 `lockup-rainbow-clear.svg`（深色、高對比用）**只能放在 `.badge-pride` 內**，目前僅用於行動紀錄頁。
- 裝飾性元素一律 `aria-hidden="true"`；**頁首站名維持真文字**，不要改成圖片。
- 網站圖示（`assets/img/favicon.svg`、`apple-touch-icon.png`、`icon-192.png`、根目錄 `favicon.ico`）來自品牌識別交件，不由腳本產生。`favicon.ico` 必須含 16／32／48 三種尺寸；換圖示時這些檔案一起換。
- 品牌原始檔（含設計規格書）在 repo 之外，色票與使用規範以規格書為準；需要時向站長索取。

## 9. 哪些內容是自動產生的

以下區塊由腳本寫進 HTML 的註解標記之間，**不要手改標記之間的內容**（會被覆寫，`check.py` 也會報錯）：

| 內容 | 唯一來源 | 腳本 | 何時自動執行 |
|---|---|---|---|
| 頁首、頁尾、閱讀設定（`<!--shared:…-->`） | `authoring/partials/` | `build-shared.py` | 片段檔有變更時由 pre-commit 執行 |
| 文章列表、上下篇、首頁最新文章（`<!--lists:…-->` 等） | `data/articles.json` | `build-lists.py` | pre-commit |
| 訂閱源 `feed.xml` | `data/articles.json` | `build-feed.py` | pre-commit |
| `sitemap.xml` | 各頁的 robots 設定 | `build-sitemap.py` | pre-commit |
| 成員數「逾 N 位」（`<!--members:…-->`） | Discord 邀請連結 | `build-members.py` | pre-commit（連不上只警告） |
| 分享圖 `og.jpg`、`assets/img/og/<slug>.jpg` | `authoring/og/*.html` | `build-og.py`（需要 Chrome 與 macOS） | 文章有變更時由 pre-commit 執行 |

- `build-shared.py`、`build-lists.py`、`build-feed.py` 都有 `--check`，可以單獨確認某一類產物是不是最新。
- **成員數只能在本機取得後靜態寫入，不要改成在訪客端用 JS 呼叫 Discord API**：那樣會讓訪客的瀏覽器連到 Discord，違反隱私說明（見 PR #16）。
- 改站名、標語或分享卡設計（`authoring/og/card.html`）後，要手動執行 `python3 authoring/build-og.py` 並提交產物。

## 10. 新增頁面

1. 複製既有頁面，保留 `<head>`（canonical、og:url 寫完整網址，網域以 `CNAME` 為準）與三組 `<!--shared:…-->` 標記。
2. 保留切頁轉場需要的 `<link rel="expect" href="#page-end" blocking="render">` 和 `</footer>` 後的 `<span id="page-end" hidden></span>`，少了切頁會閃白。
3. 在 `authoring/partials/header.html` 的導覽加一項。
4. 執行 `python3 authoring/build-shared.py` 和 `python3 authoring/build-sitemap.py`，再跑 `check.py`。

## 11. 初次設定（只需做一次）

```bash
git config core.hooksPath .githooks
git config commit.template .gitmessage
git config pull.ff only && git config push.autoSetupRemote true && git config fetch.prune true
```

GitHub 端（CI 已在 main 跑過一次後）：`bash authoring/setup-github.sh`（squash only、自動刪分支、保護 main）。

## 12. 緊急情況

站長可用 `ALLOW_MAIN_COMMIT=1` / `ALLOW_MAIN_PUSH=1` 略過本機 hook，僅限網站壞掉需要立刻處理時；事後補 PR 或 issue 說明。
