# bcdl

Download all items from a Bandcamp user's collection.

## Requirements

- [uv](https://docs.astral.sh/uv/)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp)

Install yt-dlp with:

```bash
brew install yt-dlp
```

## Installation

```bash
git clone https://github.com/jolilius/bcdl.git
cd bcdl
uv sync
```

If you use [direnv](https://direnv.net/), the virtualenv is activated automatically when you enter the directory. Otherwise activate it manually:

```bash
source .venv/bin/activate
```

## Usage

### Download a collection

```bash
bcdl <username>
```

Downloads every item in the user's public Bandcamp collection, one at a time, with a 10-second pause between each download.

### Export collection to CSV

```bash
bcdl <username> --export-csv collection.csv
```

Saves the collection as a CSV file (columns: `artist`, `title`, `url`, `item_type`) without downloading any audio.

### Downloading purchased content

Purchased items require authentication. Export your browser cookies in Netscape format (e.g. with the [Get cookies.txt LOCALLY](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) Chrome extension) and pass them with `--cookies`:

```bash
bcdl <username> --cookies cookies.txt
```

### Options

| Flag | Default | Description |
|------|---------|-------------|
| `--cookies FILE` | — | Netscape cookies file for purchased content |
| `--export-csv FILE` | — | Export collection to CSV instead of downloading |
| `--delay SECONDS` | `10` | Seconds to wait between downloads |

## Development

Run the test suite:

```bash
uv run pytest
```
