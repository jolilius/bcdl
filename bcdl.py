#!/usr/bin/env python3
"""bcdl.py - Download all items from a Bandcamp user's collection.

Usage:
    python bcdl.py <username>
    python bcdl.py <username> --cookies cookies.txt
    python bcdl.py <username> --delay 30
"""

import argparse
import csv
import json
import os
import random
import shutil
import sys
import tempfile
import time
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


COLLECTION_API = "https://bandcamp.com/api/fancollection/1/collection_items"
DEFAULT_DELAY = 10
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

TRANSIENT_PATTERNS = [
    "HTTP Error 429",
    "HTTP Error 5",      # covers 500/502/503/504
    "Connection reset",
    "timed out",
    "RemoteDisconnected",
]
PERMANENT_PATTERNS = [
    "HTTP Error 404",
    "HTTP Error 401",
    "HTTP Error 403",
    "Unsupported URL",
]

SUPPORTED_FORMATS = ("flac", "mp3", "wav", "aac", "opus")


def classify_yt_dlp_error(stderr: str) -> str:
    """Classify yt-dlp stderr as 'transient', 'permanent', or 'unknown'.
    Permanent patterns checked first — a 403 mixed with 429 is permanent."""
    for pattern in PERMANENT_PATTERNS:
        if pattern in stderr:
            return "permanent"
    for pattern in TRANSIENT_PATTERNS:
        if pattern in stderr:
            return "transient"
    return "unknown"


def _run_yt_dlp(cmd: list[str]) -> tuple[int, str]:
    """Run yt-dlp, suppress stdout, capture stderr. Returns (returncode, stderr)."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode, result.stderr


def _extract_error_summary(stderr: str) -> str:
    """Extract first ERROR: line from stderr for display, truncated to 80 chars."""
    for line in stderr.splitlines():
        if line.startswith("ERROR:"):
            return line[7:].strip()[:80]
    return "unknown error"


def load_state(path: Path) -> dict:
    """Load state file. Returns {} on missing file or corrupt JSON (with stderr warning)."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: state file unreadable ({e}), starting fresh", file=sys.stderr)
        return {}


def save_state(state: dict, path: Path) -> None:
    """Atomic write: NamedTemporaryFile(dir=path.parent) + os.replace. Creates parent dir if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tf:
        json.dump(state, tf, indent=2)
        tmp_path = tf.name
    os.replace(tmp_path, path)


def get_page_data(username: str) -> dict:
    url = f"https://bandcamp.com/{username}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    pagedata = soup.find("div", id="pagedata")
    if not pagedata:
        raise ValueError(
            f"No page data found — is '{username}' a valid Bandcamp username?"
        )
    return json.loads(pagedata["data-blob"])


def get_all_collection_items(username: str) -> list[dict]:
    data = get_page_data(username)

    fan_id = data["fan_data"]["fan_id"]
    coll_data = data.get("collection_data", {})

    # The first batch of items is embedded directly in the page HTML.
    items: list[dict] = list(
        data.get("item_cache", {}).get("collection", {}).values()
    )
    last_token: str | None = coll_data.get("last_token")

    # Paginate through the rest via the API.
    while last_token:
        payload = {
            "fan_id": fan_id,
            "older_than_token": last_token,
            "count": 20,
        }
        resp = requests.post(
            COLLECTION_API, json=payload, headers=HEADERS, timeout=30
        )
        resp.raise_for_status()

        batch = resp.json()
        batch_items: list[dict] = batch.get("items", [])
        items.extend(batch_items)

        if batch.get("more_available") and batch_items:
            last_token = batch.get("last_token")
        else:
            break

    return items


def export_csv(items: list[dict], path: str) -> None:
    fields = ["artist", "title", "url", "item_type"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for item in items:
            writer.writerow({
                "artist": item.get("band_name") or "",
                "title": item.get("album_title") or item.get("item_title") or "",
                "url": item.get("item_url") or item.get("tralbum_url") or "",
                "item_type": item.get("tralbum_type") or "",
            })
    print(f"Saved {len(items)} item(s) to {path}")


def _backoff_delay(attempt: int, base: float = 5.0, cap: float = 60.0) -> float:
    """Sleep base * 2^attempt seconds, capped, with +25% jitter. Returns actual delay."""
    delay = min(base * (2 ** attempt), cap)
    jitter = delay * 0.25 * random.random()
    actual = delay + jitter
    time.sleep(actual)
    return actual


def download_with_retry(
    item: dict,
    index: int,
    total: int,
    cookies_file: str | None = None,
    audio_format: str | None = None,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> tuple[bool, str]:
    """Download item with retry on transient errors.
    Returns (success, error_reason). error_reason is "" on success."""
    url = item.get("item_url") or item.get("tralbum_url")
    artist = item.get("band_name") or "Unknown Artist"
    title = item.get("album_title") or item.get("item_title") or "Unknown"

    if not url:
        return False, "no URL"

    cmd = ["yt-dlp", "--quiet", "--no-progress", url]
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    if audio_format:
        cmd += ["-x", "--audio-format", audio_format]

    width = len(str(total))
    print(f"[{index:{width}}/{total}] {artist} \u2014 {title}: ", end="", flush=True)

    for attempt in range(max_retries + 1):
        returncode, stderr = _run_yt_dlp(cmd)

        if returncode == 0:
            print("OK")
            return True, ""

        error_class = classify_yt_dlp_error(stderr)

        if error_class in ("permanent", "unknown"):
            reason = _extract_error_summary(stderr)
            print(f"FAILED ({reason})")
            return False, reason

        # transient — retry with backoff
        if attempt < max_retries:
            actual_delay = _backoff_delay(attempt, base_delay)
            print(f"\n  [retry {attempt + 1}/{max_retries}] waiting {actual_delay:.0f}s\u2026", end="", flush=True)
        else:
            reason = _extract_error_summary(stderr)
            print(f"FAILED (retried {max_retries}x: {reason})")
            return False, f"retried {max_retries}x: {reason}"

    return False, "max retries exceeded"  # unreachable but satisfies type checker


def download_item(
    item: dict, index: int, total: int, cookies_file: str | None = None
) -> bool:
    url: str | None = item.get("item_url") or item.get("tralbum_url")
    title: str = item.get("album_title") or item.get("item_title") or "Unknown"
    artist: str = item.get("band_name") or "Unknown Artist"

    print(f"[{index}/{total}] {artist} — {title}")

    if not url:
        print("  [!] Skipping — no URL found for this item")
        return False

    print(f"       {url}")

    cmd = ["yt-dlp", url]
    if cookies_file:
        cmd += ["--cookies", cookies_file]

    result = subprocess.run(cmd)
    return result.returncode == 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download all items from a Bandcamp user's collection"
    )
    parser.add_argument("username", help="Bandcamp username")
    parser.add_argument(
        "--cookies",
        metavar="FILE",
        help="Netscape-format cookies file for downloading purchased content",
    )
    parser.add_argument(
        "--delay",
        type=int,
        default=DEFAULT_DELAY,
        metavar="SECONDS",
        help=f"Seconds to wait between downloads (default: {DEFAULT_DELAY})",
    )
    parser.add_argument(
        "--export-csv",
        metavar="FILE",
        help="Export collection to a CSV file instead of downloading",
    )
    parser.add_argument(
        "--format",
        metavar="FORMAT",
        help=f"Audio format for downloads ({', '.join(SUPPORTED_FORMATS)})",
    )
    args = parser.parse_args()

    if shutil.which("yt-dlp") is None:
        print(
            "Error: yt-dlp is not installed. Install it with: pip install yt-dlp",
            file=sys.stderr,
        )
        sys.exit(1)

    if args.format is not None and args.format not in SUPPORTED_FORMATS:
        print(
            f"Error: unsupported format '{args.format}'. "
            f"Choose from: {', '.join(SUPPORTED_FORMATS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Fetching collection for: {args.username}")
    try:
        items = get_all_collection_items(args.username)
    except requests.HTTPError as e:
        print(f"HTTP error fetching collection: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if not items:
        print("No items found in collection.")
        sys.exit(0)

    print(f"Found {len(items)} item(s)\n")

    if args.export_csv:
        export_csv(items, args.export_csv)
        sys.exit(0)

    state_path = Path(".bcdl") / f"{args.username}.json"
    state = load_state(state_path)

    skipped = 0
    failed: list[tuple[dict, str]] = []
    for i, item in enumerate(items, 1):
        item_id = str(item.get("sale_item_id", ""))
        artist = item.get("band_name") or "Unknown Artist"
        title = item.get("album_title") or item.get("item_title") or "Unknown"

        if item_id and item_id in state:
            print(f"[skip] {artist} \u2014 {title}")
            skipped += 1
            continue

        success, reason = download_with_retry(
            item, i, len(items),
            cookies_file=args.cookies,
            audio_format=args.format,
        )
        if not success:
            failed.append((item, reason))
        elif item_id:
            state[item_id] = {
                "artist": artist,
                "title": title,
                "url": item.get("item_url") or item.get("tralbum_url") or "",
                "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            save_state(state, state_path)

        if i < len(items):
            time.sleep(args.delay)

    downloaded = len(items) - len(failed) - skipped
    print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {len(failed)} failed.")
    if failed:
        print("Failed items:")
        for item, reason in failed:
            title = item.get("album_title") or item.get("item_title") or "Unknown"
            artist = item.get("band_name") or "Unknown Artist"
            print(f"  - {artist} \u2014 {title} ({reason})")


if __name__ == "__main__":
    main()
