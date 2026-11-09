#!/usr/bin/env python3
r"""
Rename screenshots based on their content (using Claude's vision model),
then archive everything that isn't from today into monthly subfolders.

  Before: Screenshot 2026-11-08 at 12.35.10 PM.png
  After:  slack-thread-about-q3-budget_2026-11-08.png

Layout after a run:
  Screenshots/                 <- only today's screenshots
  Screenshots/Archive/2026-11/ <- older ones, by month
  Screenshots/Archive/2026-10/

Screenshots folder: macOS ~/Desktop/Screenshots, Windows Pictures\Screenshots
(override with the SCREENSHOTS_DIR environment variable).

Usage:
  python3 rename_screenshots.py --dry-run       # preview only, changes nothing
  python3 rename_screenshots.py                 # rename + archive
  python3 rename_screenshots.py --no-archive    # rename only
  python3 rename_screenshots.py --archive-only  # archive only, no API calls
  python3 rename_screenshots.py ~/Desktop       # process another folder
                                                # (older ones go to the same Archive)

Every rename and move is logged to rename_log.csv in the Screenshots folder.
"""
import argparse
import base64
import csv
import io
import os
import re
import shutil
import sys
from datetime import datetime, date
from pathlib import Path

MODEL = "claude-haiku-5-5"  # fast and cheap; good enough for naming


def default_screenshots_dir() -> Path:
    """Where screenshots are saved. Override with the SCREENSHOTS_DIR env var."""
    if os.environ.get("SCREENSHOTS_DIR"):
        return Path(os.environ["SCREENSHOTS_DIR"]).expanduser()
    if sys.platform == "win32":
        # Windows 10/11 default; OneDrive often redirects Pictures
        onedrive = os.environ.get("OneDrive")
        if onedrive and (Path(onedrive) / "Pictures" / "Screenshots").is_dir():
            return Path(onedrive) / "Pictures" / "Screenshots"
        return Path.home() / "Pictures" / "Screenshots"
    return Path.home() / "Desktop" / "Screenshots"   # macOS


SCREENSHOTS_DIR = default_screenshots_dir()
ARCHIVE_DIR = SCREENSHOTS_DIR / "Archive"
LOG_PATH = SCREENSHOTS_DIR / "rename_log.csv"

EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
# Default macOS/Windows/tool screenshot names (still need renaming)
DEFAULT_NAME = re.compile(r"^(Screenshot|Screen Shot|CleanShot|Capture)", re.IGNORECASE)
# Names this script produces: name_YYYY-MM-DD.png (or name_YYYY-MM-DD-2.png)
RENAMED = re.compile(r"_(\d{4}-\d{2}-\d{2})(?:-\d+)?\.[A-Za-z]+$")
MAX_EDGE = 1568  # downscale big Retina captures before sending

PROMPT = (
    "Describe this screenshot as a short filename: 3 to 7 words, lowercase, "
    "words separated by hyphens, no file extension, no punctuation. Focus on the "
    "app or website and what is shown, e.g. 'slack-thread-about-q3-budget' or "
    "'google-maps-route-to-airport'. Reply with the filename only."
)


# ---------- helpers ----------

def is_image(f: Path) -> bool:
    return f.is_file() and f.suffix.lower() in EXTS


def is_screenshot(f: Path) -> bool:
    """A default-named screenshot or one this script already renamed."""
    return is_image(f) and bool(DEFAULT_NAME.match(f.name) or RENAMED.search(f.name))


def shot_date(f: Path) -> date:
    """Date from our _YYYY-MM-DD suffix if present, otherwise file mod time."""
    m = RENAMED.search(f.name)
    if m:
        try:
            return datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return datetime.fromtimestamp(f.stat().st_mtime).date()


def unique_path(path: Path) -> Path:
    """Append -2, -3, ... if the name is already taken."""
    if not path.exists():
        return path
    i = 2
    while True:
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def log(action: str, old: Path, new: Path):
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_PATH, "a", newline="") as fh:
        csv.writer(fh).writerow(
            [datetime.now().isoformat(timespec="seconds"), action, str(old), str(new)])


# ---------- rename ----------

def encode_image(path: Path) -> str:
    from PIL import Image
    with Image.open(path) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_EDGE, MAX_EDGE))
        buf = io.BytesIO()
        im.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode()


def slugify(text: str) -> str:
    text = text.strip().splitlines()[0].lower() if text.strip() else ""
    text = re.sub(r"\.(png|jpe?g|gif|webp)$", "", text)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:80] or "screenshot"


def describe(client, path: Path, model: str) -> str:
    msg = client.messages.create(
        model=model,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {
                    "type": "base64", "media_type": "image/jpeg",
                    "data": encode_image(path)}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    # Skip thinking blocks; use the first text block
    text = next((b.text for b in msg.content if getattr(b, "type", "") == "text"), "")
    return slugify(text)


def rename_all(folder: Path, model: str, dry_run: bool, process_all: bool):
    files = sorted(
        f for f in folder.iterdir()
        if is_image(f) and (DEFAULT_NAME.match(f.name) or
                            (process_all and not RENAMED.search(f.name)))
    )
    if not files:
        print("Rename: nothing to rename.\n")
        return
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set.")

    import anthropic
    client = anthropic.Anthropic()
    print(f"Rename: {len(files)} file(s)\n")
    renamed = 0
    for f in files:
        try:
            slug = describe(client, f, model)
            d = shot_date(f).strftime("%Y-%m-%d")
            new = unique_path(f.with_name(f"{slug}_{d}{f.suffix.lower()}"))
            print(f"  {f.name}\n    -> {new.name}")
            if not dry_run:
                f.rename(new)
                log("rename", f, new)
                renamed += 1
        except Exception as e:
            print(f"  {f.name}\n    !! skipped: {e}")
    print(f"\n  {'Would rename' if dry_run else 'Renamed'} "
          f"{len(files) if dry_run else renamed} file(s).\n")


# ---------- archive ----------

def archive_old(folder: Path, dry_run: bool):
    today = date.today()
    old = sorted(f for f in folder.iterdir()
                 if is_screenshot(f) and shot_date(f) < today)
    if not old:
        print("Archive: nothing older than today.\n")
        return
    print(f"Archive: {len(old)} file(s) older than today\n")
    for f in old:
        month_dir = ARCHIVE_DIR / shot_date(f).strftime("%Y-%m")
        dest = unique_path(month_dir / f.name)
        print(f"  {f.name}\n    -> Archive/{month_dir.name}/{dest.name}")
        if not dry_run:
            month_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(f), str(dest))
            log("archive", f, dest)
    print()


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser(description="Rename screenshots by content and archive old ones.")
    ap.add_argument("folder", nargs="?", default=str(SCREENSHOTS_DIR))
    ap.add_argument("--dry-run", action="store_true", help="preview, change nothing")
    ap.add_argument("--all", action="store_true",
                    help="also rename images that don't have a default screenshot name")
    ap.add_argument("--no-archive", action="store_true", help="skip the archive step")
    ap.add_argument("--archive-only", action="store_true", help="skip renaming")
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    folder = Path(args.folder).expanduser()
    if not folder.is_dir():
        sys.exit(f"Folder not found: {folder}")

    print(f"Folder: {folder}{'   [DRY RUN]' if args.dry_run else ''}\n")
    if not args.archive_only:
        rename_all(folder, args.model, args.dry_run, args.all)
    if not args.no_archive:
        archive_old(folder, args.dry_run)
    if args.dry_run:
        print("Dry run only, nothing changed.")
    else:
        print(f"Done. Log: {LOG_PATH}")


if __name__ == "__main__":
    main()
