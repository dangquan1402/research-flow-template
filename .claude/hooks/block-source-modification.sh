#!/bin/bash
# PreToolUse hook: Block modifications to existing source files (immutable after creation)
# Sources are write-once. Only new files allowed.

TOOL_NAME="$1"
FILE_PATH="$2"

# Only check Edit tool (Write creates new files, Edit modifies existing)
if [[ "$TOOL_NAME" != "Edit" ]]; then
  exit 0
fi

# Block editing files in sources/
if [[ "$FILE_PATH" == *"sources/"* && "$FILE_PATH" != *".gitkeep"* ]]; then
  echo "BLOCKED: Source files are immutable after creation. Do not modify sources/. Create a new finding in memory/findings/ instead."
  exit 1
fi
