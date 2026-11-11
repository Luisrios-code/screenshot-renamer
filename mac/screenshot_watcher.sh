#!/bin/zsh
# Runs automatically (via launchd) whenever ~/Desktop/Screenshots changes.
#  1. Copies the new screenshot to the clipboard, ready to paste.
#     Multi-screen captures (Cmd-Shift-3): copies the screen the pointer is on.
#     The other screens' images are kept and renamed as usual.
#  2. Renames it by content and archives anything not from today.
# Log: ~/Library/Logs/screenshot_watcher.log

source ~/.zshrc 2>/dev/null          # picks up PATH and ANTHROPIC_API_KEY
HERE="${0:A:h}"                       # folder this script lives in
DIR="${SCREENSHOTS_DIR:-$HOME/Desktop/Screenshots}"
STATE="$HOME/.screenshot_watcher_last"
LOCK="/tmp/screenshot_watcher.lock"
LOG="$HOME/Library/Logs/screenshot_watcher.log"

# Which screen is the pointer on? 1 = main display, 2 = next, ...
# Matches macOS naming: "Screenshot ... .png" = main, "... (2).png" = next.
pointer_screen() {
  osascript -l JavaScript -e '
    ObjC.import("AppKit");
    var p = $.NSEvent.mouseLocation, s = $.NSScreen.screens, r = 1;
    for (var i = 0; i < s.count; i++) {
      var f = s.objectAtIndex(i).frame;
      if (p.x >= f.origin.x && p.x <= f.origin.x + f.size.width &&
          p.y >= f.origin.y && p.y <= f.origin.y + f.size.height) { r = i + 1; break; }
    }
    r;' 2>/dev/null || echo 1
}

# --- 1. copy new screenshot to clipboard ---
newest=$(ls -t "$DIR"/Screenshot*.png 2>/dev/null | head -1)
if [[ -n "$newest" ]]; then
  base=$(print -r -- "$newest" | sed -E 's/( \([0-9]+\))?\.png$//')
  last=$(cat "$STATE" 2>/dev/null)
  age=$(( $(date +%s) - $(stat -f %m "$newest") ))
  if [[ "$base" != "$last" && "$base.png" != "$last" && $age -lt 60 ]]; then
    sleep 1                            # let every screen's file finish saving
    pick="$base.png"
    if [[ -e "$base (2).png" ]]; then  # multi-screen capture
      n=$(pointer_screen)
      [[ "$n" -gt 1 && -e "$base ($n).png" ]] && pick="$base ($n).png"
    fi
    [[ -e "$pick" ]] || pick="$newest"
    osascript -e "set the clipboard to (read (POSIX file \"$pick\") as «class PNGf»)" \
      && echo "$base" > "$STATE" \
      && echo "$(date '+%F %T') copied: $pick" >> "$LOG"
  fi
fi

# --- 2. rename + archive (one run at a time) ---
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK"' EXIT
  python3 "$HERE/rename_screenshots.py" >> "$LOG" 2>&1
fi
