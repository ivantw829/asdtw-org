# 工作流程

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

開分支 → 檢查 → commit → push → 開 PR → CI 通過後自動 squash merge → 同步本機。

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

## 4. 新增一場行動紀錄

1. `git switch -c content/<slug>`
2. 在 `actions.html` 的時間軸 `<ol class="timeline">` **最上方**（新到舊）複製一個 `<li>`，改 `id`、標籤、標題、`<time datetime>`、地點與說明。
3. 首頁「最近的行動」只列最新 3 場，同步更新 `index.html`。
4. `bash authoring/ship.sh "content(actions): 新增〈行動名稱〉紀錄"`

## 4.1 發表文章

文章頁由 Markdown 原稿產生，不要手寫或手改產生的 HTML（重跑會被覆蓋）。

1. 照 `authoring/article-sample.md` 的格式寫原稿（想先看版型，可在本機對它跑 md2article，看完刪掉產出的頁面與 JSON 那一筆，不要提交）（frontmatter：`title`、`slug`、`date`、`category`、`tags`、`summary`、`lead`，選填 `author`、`action`、`updated`、`draft`）。分類只有「行動記事、社群公告、議題觀點、技術教學」；副標籤先看 `data/articles.json` 已有哪些，意思相近就沿用。
2. `python3 authoring/md2article.py 原稿.md --images 圖片資料夾`：產生 `articles/<slug>.html`、登錄 `data/articles.json`、轉 webp、產分享圖（需 Chrome）、更新列表／上下篇／訂閱源／sitemap，最後跑 `check.py`。改稿後重跑同一份原稿即更新。
3. 本機預覽 `/articles/<slug>.html` 與 `/articles.html`，確認後 `bash authoring/ship.sh "content(article): 新增〈標題〉"`。

- 作者可用筆名，沒填就是社群名義；未經本人同意不寫成員的真名。
- 不放現場照片與成員截圖；說明用的圖重畫成示意圖，圖說標明「示意圖」，圖中資訊在正文也要有文字。
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
- 首頁需有 Organization＋WebSite JSON-LD，內頁需有 BreadcrumbList（最後一項須等於 canonical）。
- 改站名、標語或分享圖設計後執行 `python3 authoring/build-og.py`（需 Chrome）並提交 `assets/img/` 的產物；`og.jpg` 必須是 1200×630、小於 300KB。
- 文章頁的分享圖是 `assets/img/og/<slug>.jpg`（`authoring/og/article-card.html` 產生），標題或分類改了會被判定過期，`check.py` 會提示重產。

## 7. 隱私與內容守則

- **不放照片，不列成員名單。** 這是社群的決定，用來保護身心障礙者與性別少數成員。
- 不提交：金鑰、私人信件、成員的全名與聯絡方式、可辨識的未成年人資訊。已提交的敏感內容即使刪除仍留在歷史裡，提交前請確認。
- 不使用 Cookie、分析或追蹤碼，不載入外部字體與腳本；若要新增，須先更新「隱私說明」。
- 提交信箱使用 GitHub noreply 位址。

## 8. 初次設定（只需做一次）

```bash
git config core.hooksPath .githooks
git config commit.template .gitmessage
git config pull.ff only && git config push.autoSetupRemote true && git config fetch.prune true
```

GitHub 端（CI 已在 main 跑過一次後）：`bash authoring/setup-github.sh`（squash only、自動刪分支、保護 main）。

## 9. 緊急情況

站長可用 `ALLOW_MAIN_COMMIT=1` / `ALLOW_MAIN_PUSH=1` 略過本機 hook，僅限網站壞掉需要立刻處理時；事後補 PR 或 issue 說明。
