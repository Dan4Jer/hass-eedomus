#!/bin/bash
# Install this repository's git hooks (ticket 115).
# Sets core.hooksPath to the versioned hooks directory so the hook
# file itself is committed and always in sync with the branch.
# Idempotent: safe to run again. Per-machine: one run per clone.

set -e
ROOT="$(git rev-parse --show-toplevel)"

git config core.hooksPath "$ROOT/scripts/hooks"
echo "✅ core.hooksPath = $ROOT/scripts/hooks"
echo "   The pre-push format gate (black + isort) is now active."
echo ""
echo "   Per-machine step: run this script again on every clone/machine"
echo "   that pushes this repository."
