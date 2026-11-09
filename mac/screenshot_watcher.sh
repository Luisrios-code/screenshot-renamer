#!/bin/zsh
# Runs automatically (via launchd) whenever ~/Desktop/Screenshots changes.
#  1. Copies the newest screenshot to the clipboard, ready to paste.
#  2. Renames it by content and archives anything not from today.
# Log: ~/Library/Logs/screenshot_watcher.log

source ~/.zshrc 2>/dev/null          # picks up PATH and ANTHROPIC_API_KEY
HERE="${0:A:h}"                       # folder this script lives in
DIR="${SCREENSHOTS_DIR:-$HOME/Desktop/Screenshots}"
STATE="$HOME/.screenshot_watcher_last"
LOCK="/tmp/screenshot_watcher.lock"
LOG="$HOME/Library/Logs/screenshot_watcher.log"

# --- 1. copy newest new screenshot to clipboard ---
newest=$(ls -t "$DIR"/Screenshot*.png 2>/dev/null | head -1)
if [[ -n "$newest" ]]; then
  last=$(cat "$STATE" 2>/dev/null)
  age=$(( $(date +%s) - $(stat -f %m "$newest") ))
  if [[ "$newest" != "$last" && $age -lt 60 ]]; then
    osascript -e "set the clipboard to (read (POSIX file \"$newest\") as «class PNGf»)" \
      && echo "$newest" > "$STATE" \
      && echo "$(date '+%F %T') copied: $newest" >> "$LOG"
  fi
fi

# --- 2. rename + archive (one run at a time) ---
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK"' EXIT
  python3 "$HERE/rename_screenshots.py" >> "$LOG" 2>&1
fi
