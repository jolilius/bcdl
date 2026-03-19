# Testing

## Framework

**pytest** with `unittest.mock` for mocking. No additional plugins.

```
tests/
├── conftest.py      # Adds project root to sys.path
└── test_bcdl.py     # All tests (202 lines)
```

Run tests:
```bash
pytest
# or
uv run pytest
```

## Test Structure

Tests are organized into **test classes per function**, each class named `TestFunctionName`:

| Class | Function Under Test | Test Count |
|-------|-------------------|------------|
| `TestGetPageData` | `bcdl.get_page_data()` | 3 |
| `TestGetAllCollectionItems` | `bcdl.get_all_collection_items()` | 3 |
| `TestExportCsv` | `bcdl.export_csv()` | 3 |
| `TestDownloadItem` | `bcdl.download_item()` | 5 |

Total: **14 unit tests**. No integration or E2E tests.

## Fixtures & Helpers

Defined in `test_bcdl.py` (not conftest) — shared within the file:

```python
# Shared test item dictionaries
ITEM_A = {...}   # album with item_url
ITEM_B = {...}   # track with tralbum_url fallback
ITEM_NO_URL = {...}  # item with no URL

def _make_page_html(fan_id, items, last_token) -> str:
    # Builds Bandcamp-shaped HTML with embedded JSON blob

def _mock_get(html) -> MagicMock:
    # Returns mock requests.Response for GET

def _mock_post(items, more_available, last_token) -> MagicMock:
    # Returns mock requests.Response for POST with collection API shape
```

pytest's `tmp_path` fixture used for CSV file writing tests.

## Mocking Strategy

All external I/O is mocked:

```python
with patch("requests.get", return_value=_mock_get(html)):
    data = bcdl.get_page_data("testuser")

with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
    result = bcdl.download_item(ITEM_A, 1, 3)
```

- `requests.get` — patched at `requests.get` (not `bcdl.requests.get`)
- `requests.post` — patched for pagination tests; `side_effect=[page2, page3]` for multi-page
- `subprocess.run` — patched to control yt-dlp exit code

## What Is Tested

**Happy paths**: successful fetch, pagination, CSV export, download

**Error paths**:
- Missing `#pagedata` div → `ValueError`
- HTTP 4xx/5xx → `requests.HTTPError`
- yt-dlp exit code 1 → `download_item` returns `False`
- Item with no URL → skipped, `subprocess.run` not called

**Pagination logic**:
- Single page (no pagination)
- Two pages (`more_available=True` then `False`)
- Empty batch stops pagination

**Field fallbacks**:
- `album_title` → `item_title` for title
- `item_url` → `tralbum_url` for URL

## What Is NOT Tested

- `main()` function (CLI entry point) — untested
- Network errors (timeouts, connection failures)
- JSON decode errors from malformed API responses
- File I/O errors in `export_csv`
- Rate limiting / delay behavior
- Resume/checkpoint behavior
- No coverage configuration (no `.coveragerc` or `[tool.coverage]`)
