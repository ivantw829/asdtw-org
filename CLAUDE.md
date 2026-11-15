# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本專案所有 AI coding agent 的共用規範在 `AGENTS.md`，由下一行匯入；**專案規則只改 `AGENTS.md`**，這裡只放 Claude Code 專用的事項。

@AGENTS.md

## Claude Code 專用

- 預覽工具請用 `.claude/launch.json` 的 `site` 設定（埠號 8765）。
- `.claude/`（含預覽用的 `launch.json`）已被 `.gitignore` 排除，不會進 repo。
