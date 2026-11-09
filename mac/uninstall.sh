#!/bin/zsh
# Turns off the background watcher. Your screenshots are not touched.
PLIST="$HOME/Library/LaunchAgents/com.screenshot-renamer.watcher.plist"
launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"
defaults write com.apple.screencapture show-thumbnail -bool true
killall SystemUIServer 2>/dev/null
echo "Watcher removed."
