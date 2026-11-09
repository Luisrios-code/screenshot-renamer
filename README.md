# Screenshot Renamer

Automatically renames screenshots by what's in them, copies each new one to the clipboard, and keeps only today's screenshots in the main folder.

```
Screenshot 2026-11-08 at 12.35.10 PM.png  →  slack-thread-about-q3-budget_2026-11-08.png
```

```
Screenshots/                  ← today's screenshots only
Screenshots/Archive/2026-11/  ← older ones, by month
Screenshots/Archive/2026-10/
```

- Names come from Claude (Anthropic API, Haiku model). Well under 1¢ per screenshot.
- Each screenshot image is sent to the Anthropic API to be described. Don't use it on screenshots you can't share with a third-party service.
- Every rename and move is logged in `Screenshots/rename_log.csv`, so you can undo any change.

You need an Anthropic API key: <https://console.anthropic.com/settings/keys> → **Create Key** (choose **Continue with an API key** if asked).

---

## macOS

Screenshots folder: `~/Desktop/Screenshots`

1. Check Python
```
python3 --version
```

2. Download this repo: green **Code** button → **Download ZIP** → unzip it into your home folder.

3. Go to the mac folder
```
cd ~/screenshot-renamer-main/mac
```

4. Install packages
```
python3 -m pip install anthropic pillow
```

5. Check for an API key
```
echo $ANTHROPIC_API_KEY
```

6. If blank, run this, paste your key, press Enter (nothing shows while you paste)
```
read -s "KEY?Paste key: "
```

7. If blank
```
echo "export ANTHROPIC_API_KEY=$KEY" >> ~/.zshrc
```

8.
```
source ~/.zshrc
```

9. Install the watcher
```
zsh install.sh
```

10. Test: press ⌘⇧4, take a screenshot, wait 3 seconds, then press ⌘V into any chat.

11. If the paste doesn't work, check the log
```
tail -20 ~/Library/Logs/screenshot_watcher.log
```

12. If the log says "Operation not permitted": System Settings → Privacy & Security → Full Disk Access → + → ⌘⇧G → `/bin/zsh` → turn it on. Then repeat step 10.

Turn it off:
```
zsh uninstall.sh
```

---

## Windows 10 / 11

Screenshots folder: `Pictures\Screenshots` (or `OneDrive\Pictures\Screenshots`). This is where **Win + PrtScn** and the Snipping Tool save screenshots.

1. Open PowerShell and check Python
```
python --version
```

2. If it's missing: install it from <https://www.python.org/downloads/> and tick **Add python.exe to PATH**, then reopen PowerShell.

3. Download this repo: green **Code** button → **Download ZIP** → unzip it to your Downloads folder.

4. Go to the windows folder
```
cd $HOME\Downloads\screenshot-renamer-main\windows
```

5. Install packages
```
python -m pip install anthropic pillow
```

6. Check for an API key
```
echo $env:ANTHROPIC_API_KEY
```

7. If blank: replace `PASTE-KEY` with your key
```
setx ANTHROPIC_API_KEY "PASTE-KEY"
```

8. If you did step 7: close PowerShell, open it again, then repeat step 4.

9. Install the watcher (it starts now and at every login)
```
python watch_screenshots.py --install
```

10. Test: press Win + PrtScn, wait 3 seconds, then press Ctrl+V into any chat.

11. If the paste doesn't work, check the log
```
Get-Content $env:LOCALAPPDATA\screenshot-renamer\watcher.log -Tail 20
```

Turn it off:
```
python watch_screenshots.py --uninstall
```

---

## Run by hand (either OS)

```
python3 rename_screenshots.py --dry-run
```
(`python` on Windows). Options: `--dry-run` preview only · `--no-archive` rename only · `--archive-only` no API calls · add a folder path to process a different folder.
