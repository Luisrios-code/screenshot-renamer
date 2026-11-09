#!/bin/zsh
# Sets up the automatic screenshot watcher on macOS.
#  - Screenshots save to ~/Desktop/Screenshots
#  - Floating thumbnail off (screenshots save instantly)
#  - Background watcher: copy to clipboard, rename, archive
set -e
HERE="${0:A:h}"
SHOTS="$HOME/Desktop/Screenshots"
LABEL="com.screenshot-renamer.watcher"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

mkdir -p "$SHOTS" "$HOME/Library/LaunchAgents" "$HOME/Library/Logs"
chmod +x "$HERE/screenshot_watcher.sh"

defaults write com.apple.screencapture location "$SHOTS"
defaults write com.apple.screencapture show-thumbnail -bool false
killall SystemUIServer 2>/dev/null || true

cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/zsh</string>
    <string>$HERE/screenshot_watcher.sh</string>
  </array>
  <key>WatchPaths</key>
  <array><string>$SHOTS</string></array>
  <key>ThrottleInterval</key><integer>2</integer>
  <key>StandardErrorPath</key><string>$HOME/Library/Logs/screenshot_watcher.log</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "Installed. Screenshots folder: $SHOTS"
echo "Log: ~/Library/Logs/screenshot_watcher.log"
