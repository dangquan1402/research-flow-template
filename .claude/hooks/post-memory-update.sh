#!/bin/bash
# PostToolUse hook: Remind to update memory index after modifying memory files
# Triggers when Edit/Write modifies files in memory/

TOOL_NAME="$1"
FILE_PATH="$2"

# Only check Edit and Write tools
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
  exit 0
fi

# Only check memory directory modifications (but not index.md or log.md themselves)
if [[ "$FILE_PATH" == *"memory/"* && "$FILE_PATH" != *"memory/index.md"* && "$FILE_PATH" != *"memory/log.md"* && "$FILE_PATH" != *"memory/entity-registry.json"* && "$FILE_PATH" != *".gitkeep"* ]]; then
  echo "REMINDER: memory/ was modified. Update memory/index.md and append to memory/log.md."
fi
