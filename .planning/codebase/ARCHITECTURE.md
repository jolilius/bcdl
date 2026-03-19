# Architecture

**Analysis Date:** 2026-03-19

## Pattern Overview

**Overall:** Layered pipeline architecture with separation between data fetching, processing, and output generation.

**Key Characteristics:**
- Single-file monolithic module with clear functional separation
- Request/response pattern for external integrations (Bandcamp API, yt-dlp subprocess)
- Linear execution flow with optional branches (CSV export vs. download)
- Command-line interface as entry point with argument parsing

## Layers

**CLI/Orchestration Layer:**
- Purpose: Parse user input and coordinate workflow
- Location: `bcdl.py` (lines 120-185)
- Contains: `main()` function with argparse setup and execution flow
- Depends on: All downstream functions (data fetching, processing, output)
- Used by: Command-line invocation via setuptools entry point

**Data Fetching Layer:**
- Purpose: Retrieve Bandcamp collection data via HTTP requests
- Location: `bcdl.py` (lines 32-79)
- Contains: `get_page_data()` and `get_all_collection_items()` functions
- Depends on: `requests` library, BeautifulSoup HTML parsing
- Used by: `main()` to populate collection before processing

**Export/Output Layer:**
- Purpose: Convert collection data to various formats
- Location: `bcdl.py` (lines 82-94 for CSV, lines 97-117 for download)
- Contains: `export_csv()` and `download_item()` functions
- Depends on: `csv` module (for CSV export), `subprocess` module (for yt-dlp invocation)
- Used by: `main()` to write results

## Data Flow

**Collection Fetch Workflow:**

1. User provides username via CLI argument
2. `main()` calls `get_all_collection_items(username)`
3. `get_page_data()` makes initial HTTP GET request to user's Bandcamp profile
4. BeautifulSoup extracts and parses JSON blob from page HTML
5. Initial batch of items extracted from embedded `item_cache`
6. If `last_token` exists, pagination loop begins via repeated POST to collection API
7. Each API response merged into growing items list
8. Loop terminates when API returns `more_available: false` or empty batch

**Output Flow (CSV Export):**

1. After fetching, user may specify `--export-csv FILE`
2. `main()` calls `export_csv(items, path)`
3. CSV file created with headers: `artist`, `title`, `url`, `item_type`
4. Item data mapped to CSV columns with fallback values for missing fields
5. Process exits after CSV write

**Output Flow (Download):**

1. If no `--export-csv` flag, `main()` enters download loop
2. For each item in collection, `download_item(item, index, total, cookies_file)` called
3. `download_item()` spawns subprocess: `yt-dlp [url]` with optional `--cookies FILE`
4. Process waits for subprocess completion and checks return code
5. On failure, item appended to failed list
6. Inter-item delay applied via `time.sleep(delay_seconds)` if not final item
7. Summary printed with success/failure counts

**State Management:**
- No persistent state. All state is in-memory within `main()` execution context
- Items list passed between functions as arguments
- Failed items accumulate in list during download loop
- No database or cache between runs

## Key Abstractions

**Item (dict):**
- Purpose: Represents a single Bandcamp album/track in user's collection
- Structure: Dict with keys like `band_name`, `album_title`, `item_title`, `item_url`, `tralbum_url`, `tralbum_type`
- Used in: All output functions as primary data unit
- Pattern: Flexible fallback pattern for optional fields (e.g., prefer `item_url` over `tralbum_url`)

**PageData (dict):**
- Purpose: Represents parsed Bandcamp user profile page data
- Structure: Contains `fan_data` (with `fan_id`), `collection_data` (pagination tokens), `item_cache` (initial items)
- Used in: `get_page_data()` extraction, `get_all_collection_items()` initialization
- Pattern: JSON blob extracted from HTML and parsed once per session

## Entry Points

**CLI Entry Point:**
- Location: `bcdl.py` (lines 184-185)
- Invoked via: `bcdl <username>` (setuptools script entry point defined in `pyproject.toml`)
- Triggers: `main()` function
- Responsibilities: Argument parsing, exception handling, user feedback, workflow coordination

**main() Function:**
- Location: `bcdl.py` (lines 120-181)
- Parameters: None (reads from `sys.argv` via argparse)
- Returns: None (calls `sys.exit()` on error)
- Responsibilities:
  - Parse CLI arguments
  - Fetch collection items
  - Route to CSV export or download workflow
  - Aggregate and report results

## Error Handling

**Strategy:** Fail-fast for collection fetching, graceful degradation for downloads

**Patterns:**

- **HTTP Errors:** `requests.HTTPError` raised during fetch; caught in `main()` and printed to stderr before exit
- **Validation Errors:** `ValueError` raised if username invalid (no pagedata found); caught in `main()` with user-friendly message
- **Download Failures:** Return code from `yt-dlp` subprocess checked; failures accumulated in list rather than halting execution
- **Missing Fields:** Fallback values used (empty string or "Unknown") for CSV export when optional fields missing

## Cross-Cutting Concerns

**Logging:** `print()` for user-facing messages; stderr used for errors via `file=sys.stderr`

**Validation:**
- HTML pagedata existence checked in `get_page_data()`
- URL existence checked in `download_item()` before spawning subprocess
- All arguments validated by argparse

**Rate Limiting:** `--delay` flag allows configurable inter-request pause (default 10s) between downloads to avoid rate limiting

---

*Architecture analysis: 2026-03-19*
