# Coding Conventions

## Language & Runtime

- **Python 3.12+** required
- Modern type hint syntax: `list[dict]`, `str | None` (PEP 585/604, no `Optional`)
- All public functions have type annotations

## Code Style

**PEP 8** followed implicitly. No linting toolchain configured (no black, ruff, pylint, mypy).

### Naming

| Entity | Convention | Example |
|--------|-----------|---------|
| Functions | `snake_case` | `get_page_data`, `export_csv` |
| Variables | `snake_case` | `last_token`, `batch_items` |
| Constants | `UPPER_CASE` | `COLLECTION_API`, `DEFAULT_DELAY` |
| Test classes | `TestFunctionName` | `TestGetPageData` |
| Test methods | `test_describes_behavior` | `test_raises_on_http_error` |

### Function Signatures

```python
def get_page_data(username: str) -> dict:
def get_all_collection_items(username: str) -> list[dict]:
def export_csv(items: list[dict], path: str) -> None:
def download_item(item: dict, index: int, total: int, cookies_file: str | None = None) -> bool:
def main() -> None:
```

## Error Handling

- HTTP errors: `resp.raise_for_status()` — surfaces `requests.HTTPError` to caller
- Missing data: explicit `raise ValueError(...)` with descriptive user-facing messages
- `main()` catches `HTTPError` and `ValueError`, prints to `stderr`, calls `sys.exit(1)`
- Subprocess errors: checks `result.returncode`, returns `False` (no exception raised)
- **No retry logic** — errors propagate or fail silently per item

## Output / Logging

- All user-facing output via `print()` — no logging library configured
- Progress format: `[{index}/{total}] {artist} — {title}`
- Errors to `stderr`: `print(f"Error: {e}", file=sys.stderr)`
- No verbosity levels or debug mode

## Patterns

**Functional style** — no classes in production code. All logic is standalone functions.

**Data shape** — Bandcamp items are raw `dict` objects passed through the pipeline unchanged. Field access uses `.get()` with fallbacks:

```python
title = item.get("album_title") or item.get("item_title") or "Unknown"
url = item.get("item_url") or item.get("tralbum_url")
```

**Constants at module level** — API URL, default delay, browser-spoofing User-Agent header defined at top of file.

**CLI via argparse** — arguments: `username` (positional), `--cookies`, `--delay`, `--export-csv`.

## Comments

Minimal but purposeful. Comments explain non-obvious behavior:

```python
# The first batch of items is embedded directly in the page HTML.
# Paginate through the rest via the API.
```

No docstrings on functions (only module-level docstring with usage).
