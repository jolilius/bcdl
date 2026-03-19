# Concerns & Technical Debt

## Critical Issues

### 1. Subprocess Safety — No Error Capture
**File:** `bcdl.py:116`
```python
result = subprocess.run(cmd)  # stdout/stderr not captured
```
yt-dlp output floods the terminal with no filtering. Errors from yt-dlp are not captured or logged. If yt-dlp is not installed, the error message is confusing.

**Risk:** Poor UX, difficult to debug failures programmatically.

### 2. No Retry Logic on API Calls
**Files:** `bcdl.py:34`, `bcdl.py:65-68`

Both `requests.get` and `requests.post` calls have no retry on transient failures (429 rate limits, 5xx errors, timeouts). A single failed page request aborts the entire collection fetch.

**Risk:** Large collections (100s of pages) will fail unpredictably on network hiccups.

### 3. JSON Decode Not Handled
**File:** `bcdl.py:43`
```python
return json.loads(pagedata["data-blob"])
```
If Bandcamp changes their HTML structure and `data-blob` is malformed or missing, this raises an unhandled `json.JSONDecodeError` or `KeyError`.

**Risk:** Cryptic crash with no user-friendly message.

### 4. Unbounded In-Memory Collection
**File:** `bcdl.py:53-77`
```python
items: list[dict] = list(...)
items.extend(batch_items)
```
All collection items are accumulated in memory before any processing. For very large collections (1000s of items), this could cause memory pressure.

**Risk:** Low for typical collections, but no streaming/batching option exists.

## Reliability Concerns

### 5. No Download Resume / Checkpointing
Downloads are fully sequential with no state persistence. If the process is killed mid-run (network drop, user Ctrl-C), there is no way to resume — the entire collection must be re-fetched and partially-downloaded items are not tracked.

### 6. Fragile HTML Scraping
**File:** `bcdl.py:37-43`
```python
pagedata = soup.find("div", id="pagedata")
```
The initial collection data is scraped from an embedded JSON blob in Bandcamp's HTML. Any DOM restructuring by Bandcamp will silently break collection fetching.

### 7. No Rate Limit Handling
The `--delay` flag adds a fixed delay between *downloads* but there's no rate limiting on the API pagination requests. Rapid pagination could trigger Bandcamp's rate limits.

## Testing Gaps

### 8. `main()` Is Untested
The CLI entry point (`main()`) has no test coverage. Argument parsing, error handling paths, and the download loop are completely untested.

### 9. No Integration Tests
All tests mock the network. There are no integration tests against real Bandcamp responses or real yt-dlp behavior.

### 10. Edge Cases Not Covered
- Empty collection (0 items)
- Network timeout during pagination
- Malformed item dicts from API
- Concurrent modification of collection during multi-page fetch

## Positive Observations

- Well-structured functions with clear single responsibilities
- Type hints present throughout production code
- Good unit test coverage for happy paths and documented error cases
- User-facing error messages are descriptive
- CSV export handles missing fields gracefully with fallbacks
- `raise_for_status()` ensures HTTP errors aren't silently swallowed

## Priority for Future Work

| Priority | Concern | Effort |
|----------|---------|--------|
| High | No retry logic (#2) | Low |
| High | No resume/checkpoint (#5) | Medium |
| Medium | Subprocess error capture (#1) | Low |
| Medium | JSON decode error handling (#3) | Low |
| Medium | `main()` test coverage (#8) | Low |
| Low | Unbounded memory (#4) | Medium |
| Low | Fragile HTML scraping (#6) | High |
