#!/usr/bin/env python3
"""
Windows background watcher for the Screenshots folder.

Every new screenshot is:
  1. copied to the clipboard (ready to paste with Ctrl+V)
  2. renamed by content, and anything not from today archived

Usage:
  python watch_screenshots.py              # run in this window (Ctrl+C to stop)
  python watch_screenshots.py --install    # start now + start at every login
  python watch_screenshots.py --uninstall  # stop starting at login

Log: %LOCALAPPDATA%\\screenshot-renamer\\watcher.log
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rename_screenshots as rs  # noqa: E402

POLL_SECONDS = 2
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
LOG_DIR = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "screenshot-renamer"
STARTUP_DIR = (Path(os.environ.get("APPDATA", "")) /
               "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup")
STARTUP_BAT = STARTUP_DIR / "screenshot_watcher.bat"


def pythonw() -> str:
    """Windowless Python, so no console window stays open."""
    w = Path(sys.executable).with_name("pythonw.exe")
    return str(w if w.exists() else sys.executable)


def copy_image_to_clipboard(path: Path):
    p = str(path).replace("'", "''")
    ps = ("Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
          f"$i=[System.Drawing.Image]::FromFile('{p}');"
          "[System.Windows.Forms.Clipboard]::SetImage($i);$i.Dispose()")
    subprocess.run(["powershell", "-NoProfile", "-STA", "-Command", ps],
                   creationflags=CREATE_NO_WINDOW, timeout=30, check=True)


def wait_until_written(path: Path, tries: int = 10):
    """Wait until the file size stops changing."""
    last = -1
    for _ in range(tries):
        try:
            size = path.stat().st_size
        except FileNotFoundError:
            return False
        if size == last and size > 0:
            return True
        last = size
        time.sleep(0.5)
    return True


def new_shots(folder: Path):
    return {f for f in folder.iterdir() if rs.is_image(f) and rs.DEFAULT_NAME.match(f.name)}


def watch():
    folder = rs.SCREENSHOTS_DIR
    folder.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if sys.stdout is None or "pythonw" in sys.executable.lower():
        log = open(LOG_DIR / "watcher.log", "a", buffering=1, encoding="utf-8")
        sys.stdout = sys.stderr = log
    (LOG_DIR / "watcher.pid").write_text(str(os.getpid()))
    print(f"{time.strftime('%F %T')} watching {folder}")

    seen = new_shots(folder)          # don't re-copy screenshots that already exist
    while True:
        try:
            current = new_shots(folder)
            fresh = sorted(current - seen, key=lambda f: f.stat().st_mtime)
            if fresh:
                newest = fresh[-1]
                if wait_until_written(newest):
                    copy_image_to_clipboard(newest)
                    print(f"{time.strftime('%F %T')} copied: {newest.name}")
                try:
                    rs.rename_all(folder, rs.MODEL, dry_run=False, process_all=False)
                    rs.archive_old(folder, dry_run=False)
                except SystemExit as e:          # e.g. API key not set
                    print(f"rename skipped: {e}")
            seen = new_shots(folder)
        except Exception as e:
            print(f"{time.strftime('%F %T')} error: {e}")
        time.sleep(POLL_SECONDS)


def install():
    STARTUP_DIR.mkdir(parents=True, exist_ok=True)
    script = Path(__file__).resolve()
    STARTUP_BAT.write_text(f'@start "" "{pythonw()}" "{script}"\r\n', encoding="utf-8")
    subprocess.Popen([pythonw(), str(script)],
                     creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW)
    print("Installed. Watcher is running and will start at every login.")
    print(f"Screenshots folder: {rs.SCREENSHOTS_DIR}")
    print(f"Log: {LOG_DIR / 'watcher.log'}")


def uninstall():
    STARTUP_BAT.unlink(missing_ok=True)
    pid_file = LOG_DIR / "watcher.pid"
    if pid_file.exists():
        subprocess.run(["taskkill", "/F", "/PID", pid_file.read_text().strip()],
                       capture_output=True)
        pid_file.unlink(missing_ok=True)
    print("Removed from startup and stopped. Your screenshots are not touched.")


if __name__ == "__main__":
    if sys.platform != "win32":
        sys.exit("This watcher is for Windows. On macOS use the mac/ folder.")
    ap = argparse.ArgumentParser(description="Watch the Screenshots folder.")
    ap.add_argument("--install", action="store_true")
    ap.add_argument("--uninstall", action="store_true")
    a = ap.parse_args()
    if a.install:
        install()
    elif a.uninstall:
        uninstall()
    else:
        watch()
