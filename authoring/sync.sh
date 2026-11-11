#!/usr/bin/env bash
# 讓本機與 GitHub 保持一致：抓取並清理遠端已刪除的分支、main 快轉到最新、刪除已合併的本機分支。
# 用法：bash authoring/sync.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

git fetch -q --prune origin
if [ -z "$(git status --porcelain)" ]; then
  git switch -q main
  git pull -q --ff-only
else
  echo "⚠ 有未提交的變更，略過切換 main。"
fi

# 遠端分支已被刪除（PR 合併後自動刪除）的本機分支 → 一併刪除
for b in $(git for-each-ref --format='%(refname:short) %(upstream:track)' refs/heads | awk '$2=="[gone]"{print $1}'); do
  if [ "$b" != "$(git branch --show-current)" ]; then
    git branch -D "$b" >/dev/null
    echo "已刪除本機分支：$b"
  fi
done

git branch -vv
if [ "$(git rev-parse main)" = "$(git rev-parse origin/main)" ]; then
  echo "✓ 本機 main 與 GitHub 一致（$(git rev-parse --short main)）"
else
  echo "⚠ 本機 main 與 GitHub 不一致" >&2
  exit 1
fi
