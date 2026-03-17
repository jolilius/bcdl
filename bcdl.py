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
import sys
import time
import subprocess

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
    args = parser.parse_args()

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


    failed: list[dict] = []
    for i, item in enumerate(items, 1):
        success = download_item(item, i, len(items), cookies_file=args.cookies)
        if not success:
            failed.append(item)

        if i < len(items):
            print(f"  Waiting {args.delay}s…\n")
            time.sleep(args.delay)

    print(f"\nDone — {len(items) - len(failed)}/{len(items)} downloaded successfully.")
    if failed:
        print("Failed items:")
        for item in failed:
            title = item.get("album_title") or item.get("item_title") or "Unknown"
            artist = item.get("band_name") or "Unknown Artist"
            print(f"  - {artist} — {title}")


if __name__ == "__main__":
    main()
