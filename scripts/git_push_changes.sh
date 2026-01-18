#!/bin/bash

# Eedomus Dynamic Configuration Panel - Git Push Script
# 
# This script pushes the committed changes to the remote repository.

echo "🚀 Starting git push process..."

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository. Please run this script from the root of your git repository."
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || git rev-parse --abbrev-ref HEAD)
echo "📋 Current branch: $CURRENT_BRANCH"

# Check if there are any commits to push
COMMITS_AHEAD=$(git rev-list --count HEAD..@{upstream} 2>/dev/null)
if [[ $? -ne 0 ]]; then
    echo "⚠️  No upstream branch configured. You may need to set it with:"
    echo "   git push --set-upstream origin $CURRENT_BRANCH"
    COMMITS_AHEAD=$(git rev-list --count HEAD 2>/dev/null || echo "unknown")
fi

if [[ "$COMMITS_AHEAD" == "0" ]]; then
    echo "✅ No new commits to push. Local branch is up to date with remote."
    exit 0
fi

echo "📝 Found $COMMITS_AHEAD commit(s) to push"

# Show the commit(s) that will be pushed
echo ""
echo "📋 Commit(s) to be pushed:"
git log --oneline HEAD..@{upstream} 2>/dev/null || git log --oneline -n $COMMITS_AHEAD

echo ""
echo "🔄 Pushing changes to remote repository..."

# Try to push
if git push origin $CURRENT_BRANCH; then
    echo "🎉 Successfully pushed changes to $CURRENT_BRANCH!"
    
    # Show the remote URL
    REMOTE_URL=$(git remote get-url origin)
    echo "📍 Pushed to: $REMOTE_URL"
    
    # Show the commit hash
    LATEST_COMMIT=$(git rev-parse HEAD)
    echo "🔗 Latest commit: $LATEST_COMMIT"
    
    exit 0
else
    echo "❌ Failed to push changes. Please check your git configuration and try again."
    echo ""
    echo "Troubleshooting tips:"
    echo "1. Make sure you have permission to push to this repository"
    echo "2. Check your internet connection"
    echo "3. Verify your SSH keys are properly configured"
    echo "4. Try: git pull --rebase before pushing if there are conflicts"
    exit 1
fi