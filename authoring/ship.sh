#!/usr/bin/env bash
# 一鍵發布：開分支 → 檢查並提交 → 推送 → 開 PR → 等 CI 通過後自動 squash merge → 同步本機。
# 用法：bash authoring/ship.sh "type(scope): 描述" [分支名]
#   在 main 上執行時會自動開新分支；在功能分支上執行則沿用該分支。
# 環境變數：CO_AUTHOR（提交共同作者）、PR_BODY（PR 內文）
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

msg="${1:?用法：bash authoring/ship.sh \"type(scope): 描述\" [分支名]}"
pattern='^(feat|fix|content|docs|style|refactor|perf|chore|ci|revert)(\([a-z0-9-]+\))?!?: .+'
printf '%s' "$msg" | grep -Eq "$pattern" || { echo "✗ 訊息不符合約定式 commit：$msg" >&2; exit 1; }
type="${msg%%[(:!]*}"

git fetch -q origin
branch=$(git branch --show-current)
if [ "$branch" = "main" ]; then
  branch="${2:-$type/$(date +%Y%m%d-%H%M%S)}"
  git switch -q -c "$branch"
fi

git add -A
if ! git diff --cached --quiet; then
  if [ -n "${CO_AUTHOR:-}" ]; then
    git commit -q -m "$msg" -m "Co-Authored-By: $CO_AUTHOR"
  else
    git commit -q -m "$msg"
  fi
elif [ -z "$(git log origin/main..HEAD --oneline)" ]; then
  echo "✗ 沒有任何變更可以發布。" >&2
  exit 1
fi

git push -q -u origin "$branch"
if ! gh pr view "$branch" >/dev/null 2>&1; then
  gh pr create --base main --head "$branch" --title "$msg" --body "${PR_BODY:-由 authoring/ship.sh 建立}" >/dev/null
fi
url=$(gh pr view "$branch" --json url --jq .url)
echo "PR：$url"

# CI 通過後由 GitHub 自動 squash merge 並刪除遠端分支
gh pr merge "$branch" --auto --squash --delete-branch >/dev/null 2>&1 || true

echo "等待 CI 與合併…（最多 5 分鐘）"
state=""
for _ in $(seq 1 60); do
  state=$(gh pr view "$branch" --json state --jq .state)
  [ "$state" = "MERGED" ] && break
  [ "$state" = "CLOSED" ] && { echo "✗ PR 被關閉" >&2; exit 1; }
  sleep 5
done
if [ "$state" != "MERGED" ]; then
  echo "⚠ 5 分鐘內尚未合併，請查看：$url（gh pr checks $branch）" >&2
  gh pr checks "$branch" || true
  exit 1
fi
echo "✓ 已合併"
bash authoring/sync.sh
