#!/usr/bin/env bash
# One-command deploy. Requires GitHub CLI: https://cli.github.com
#   macOS:   brew install gh
#   Linux:   sudo apt install gh    (or see install docs)
#   Windows: winget install GitHub.cli
#
# Usage (from inside the unzipped job-radar/ folder):
#   chmod +x deploy.sh && ./deploy.sh
set -euo pipefail

REPO_NAME="${1:-job-radar}"

command -v gh >/dev/null || { echo "❌ gh CLI not installed — see https://cli.github.com"; exit 1; }
gh auth status >/dev/null 2>&1 || gh auth login

echo "▶ Initializing git repo…"
git init -q -b main
git add .
git -c user.name="you" -c user.email="you@local" commit -q -m "initial: job-radar scaffold"

echo "▶ Creating GitHub repo '$REPO_NAME' and pushing…"
gh repo create "$REPO_NAME" --public --source=. --remote=origin --push

USER=$(gh api user --jq .login)

echo "▶ Enabling write permissions for workflows…"
gh api -X PUT "/repos/$USER/$REPO_NAME/actions/permissions/workflow" \
  -f default_workflow_permissions=write \
  -F can_approve_pull_request_reviews=false >/dev/null

echo "▶ Enabling GitHub Pages (Actions source)…"
gh api -X POST "/repos/$USER/$REPO_NAME/pages" \
  -f 'build_type=workflow' >/dev/null 2>&1 || \
gh api -X PUT  "/repos/$USER/$REPO_NAME/pages" \
  -f 'build_type=workflow' >/dev/null

echo "▶ Kicking off weekly-discovery (ATS slug scan, ~5 min)…"
gh workflow run weekly-discovery.yml || gh workflow run weekly.yml

echo
echo "✅ Done. Next steps:"
echo "   • Watch the run:   gh run watch"
echo "   • Then trigger:    gh workflow run daily-build.yml"
echo "   • Open the site:   https://$USER.github.io/$REPO_NAME/"
echo
echo "Edit resume.md and commit when you're ready — the next daily run picks it up."
