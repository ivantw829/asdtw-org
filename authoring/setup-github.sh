#!/usr/bin/env bash
# 一次性設定 GitHub repo：squash merge、自動刪分支、保護 main。
# 前提：CI 已經在 main 上至少跑過一次（才找得到 check、pr-title 這兩個檢查）。
# 用法：bash authoring/setup-github.sh
set -euo pipefail
REPO="${1:-ivantw829/asdtw-org}"

echo "→ 合併策略：只允許 squash merge，合併後自動刪分支，並啟用自動合併（CI 通過即合併）"
gh repo edit "$REPO" \
  --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false \
  --delete-branch-on-merge --enable-auto-merge

echo "→ 保護 main：必須通過 CI、必須走 PR、線性歷史、禁止強推與刪除"
gh api -X PUT "repos/$REPO/branches/main/protection" --input - <<JSON
{
  "required_status_checks": { "strict": true, "contexts": ["check", "pr-title"] },
  "enforce_admins": false,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_conversation_resolution": true
}
JSON
echo "完成。站長（admin）仍可在緊急時繞過保護。"
