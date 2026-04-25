#!/bin/bash
# PreToolUse hook: Block direct commits to main
# All work must happen on research/, hypothesis/, synthesis/, or review/ branches

TOOL_NAME="$1"

if [[ "$TOOL_NAME" != "Bash" ]]; then
  exit 0
fi

# Check if the bash command is a git commit
COMMAND="$2"
if [[ "$COMMAND" == *"git commit"* ]]; then
  BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
  if [[ "$BRANCH" == "main" ]]; then
    echo "BLOCKED: Cannot commit directly to main. Create a branch first: research/, hypothesis/, synthesis/, or review/"
    exit 1
  fi
fi
