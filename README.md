# bcdl

Download your entire Bandcamp collection with one command.

## Prerequisites

Before installing bcdl, make sure you have the following:

- **Python 3.12+** — [python.org/downloads](https://www.python.org/downloads/)
- **pipx** — install via `brew install pipx` (macOS) or `python -m pip install --user pipx`
  ([pipx docs](https://pipx.pypa.io/stable/installation/))
- **yt-dlp** — `brew install yt-dlp` or `pip install yt-dlp`
  ([yt-dlp on GitHub](https://github.com/yt-dlp/yt-dlp))
- **ffmpeg** — required when using `--format` to convert audio: `brew install ffmpeg`

## Install

### From PyPI (once published)

```bash
pipx install bcdl
```

### From source (current method)

```bash
git clone https://github.com/jolilius/bcdl.git
cd bcdl
uv build --wheel
pipx install dist/bcdl-0.1.0-py3-none-any.whl
```

Verify the install:

```bash
bcdl --help
```

## Quick Start

```bash
bcdl your-username --cookies cookies.txt
```

This downloads every item in your collection, skips anything already downloaded, and waits 10 seconds between downloads to be polite to Bandcamp's servers.

## Getting Your Cookies File

Purchased content requires authentication. To download items you own:

1. Install the **[Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc)** Chrome extension
2. Log in to [bandcamp.com](https://bandcamp.com)
3. Click the extension icon while on bandcamp.com
4. Click **Export** to save the file as `cookies.txt`
5. Move the file to the directory where you want to run bcdl
6. Run:

```bash
bcdl your-username --cookies cookies.txt
```

## Options

| Flag | Default | Description | Example |
|------|---------|-------------|---------|
| `--cookies FILE` | — | Netscape cookies file for purchased content | `bcdl user --cookies cookies.txt` |
| `--format FORMAT` | best available | Audio format: flac, mp3, wav, aac, opus | `bcdl user --format flac --cookies cookies.txt` |
| `--delay SECONDS` | 10 | Wait time in seconds between downloads | `bcdl user --delay 30 --cookies cookies.txt` |
| `--export-csv FILE` | — | Export collection to CSV (no download) | `bcdl user --export-csv collection.csv` |

## How It Works

### Resume

bcdl remembers what it has already downloaded. State is stored in `.bcdl/{username}.json`. If interrupted (Ctrl-C), just run the same command again — it picks up where it left off. Already-downloaded items are skipped automatically.

### Output format

Each item shows `[N/M] Artist — Title: OK` or `FAILED`. Transient errors (rate limits, timeouts) are retried automatically up to 3 times before marking an item as failed.

### Summary

After each run, a summary shows total downloaded, skipped, and failed counts:

```
Done: 42 downloaded, 10 skipped, 1 failed.
```

## Development

```bash
git clone https://github.com/jolilius/bcdl.git
cd bcdl
uv sync
uv run pytest
```
