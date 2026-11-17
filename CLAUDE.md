# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本專案所有 AI coding agent 的共用規範在 `AGENTS.md`，由下一行匯入；**專案規則只改 `AGENTS.md`**，這裡只放 Claude Code 專用的事項。

@AGENTS.md

## Claude Code 專用

- 預覽工具請用 `.claude/launch.json` 的 `site` 設定（埠號 8765）。
- `.claude/`（含預覽用的 `launch.json`）已被 `.gitignore` 排除，不會進 repo。
- 在 `.claude/worktrees/` 的 worktree 工作時，分支名是 `claude/…`；用 `ship.sh` 發布前先 `git branch -m <type>/<名稱>`，讓分支前綴對應約定式 commit 的 type。`ship.sh` 最後的 `sync.sh` 會因 `main` 已被主資料夾佔用而出現 `fatal: 'main' is already used by worktree`：此時 PR 已合併，可以忽略，之後到主資料夾執行 `bash authoring/sync.sh` 即可。
- 8765 埠被其他 worktree 的預覽佔用時，改用 `launch.json` 的 `site-alt`（8766）。
