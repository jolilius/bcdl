# External Integrations

**Analysis Date:** 2026-03-19

## APIs & External Services

**Bandcamp Collection API:**
- Service: Bandcamp (https://bandcamp.com)
- What it's used for: Fetching user's collection items and paginating through results
  - Endpoint: `https://bandcamp.com/api/fancollection/1/collection_items` (POST)
  - SDK/Client: requests library (raw HTTP client)
  - Auth: Via browser cookies (Netscape format, optional)
  - Implementation: `bcdl.py:get_all_collection_items()` and `get_page_data()`

**Bandcamp User Pages:**
- Service: Bandcamp (https://bandcamp.com/{username})
- What it's used for: Scraping initial collection data embedded in HTML page
  - Endpoint: `https://bandcamp.com/{username}` (GET)
  - Auth: Optional browser cookies for private collections
  - Implementation: HTML page is parsed for `<div id="pagedata">` containing JSON-encoded blob

## Data Storage

**Databases:**
- None - this is a CLI tool with no database backend

**File Storage:**
- Local filesystem only
  - CSV export: Optional `--export-csv` flag writes to local file
  - Cookies: Optional `--cookies` parameter points to local Netscape-format cookies file

**Caching:**
- None - each run fetches fresh data from Bandcamp

## Authentication & Identity

**Auth Provider:**
- None - Bandcamp authentication is optional
- Custom approach: Browser cookies
  - Implementation: User manually exports cookies from browser and passes `--cookies cookies.txt` flag
  - Tools: Get cookies.txt LOCALLY Chrome extension recommended in README
  - Format: Netscape-format cookies file
  - Use case: Accessing purchased/private items

## Monitoring & Observability

**Error Tracking:**
- None - basic error messages printed to stderr via `sys.stderr`

**Logs:**
- Console output only
  - Info messages to stdout (progress, counts, results)
  - Errors to stderr (HTTP errors, missing data)

## CI/CD & Deployment

**Hosting:**
- None - CLI tool designed for local execution
- Distributed via GitHub repository

**CI Pipeline:**
- None configured - repository has basic git history only

## Environment Configuration

**Required env vars:**
- None - tool is configured entirely via CLI arguments

**Optional env vars:**
- None used; all configuration is command-line argument based

**Secrets location:**
- Secrets (cookies) are passed as file path to `--cookies` flag
- No secrets stored in code or config files

## Webhooks & Callbacks

**Incoming:**
- None

**Outgoing:**
- None - tool only makes outbound HTTP requests to Bandcamp

## External Tool Dependencies

**yt-dlp:**
- Purpose: Actual download of audio/video content from Bandcamp URLs
- Integration: Invoked as subprocess in `bcdl.py:download_item()`
- Installation: `brew install yt-dlp` (macOS) or equivalent on other platforms
- Not a Python dependency - called as external command
- Command: `subprocess.run(["yt-dlp", url, optional_cookies_flag])`

---

*Integration audit: 2026-03-19*
