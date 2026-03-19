# Architecture Research

**Domain:** Python CLI downloader with state/resume tracking
**Researched:** 2026-03-19
**Confidence:** HIGH (based on codebase analysis + established Python CLI patterns)

## Standard Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                        CLI Layer (main)                          │
│   argparse → arg validation → workflow routing → exit codes      │
├──────────────────────────────────────────────────────────────────┤
│                      Orchestration Layer                         │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐  │
│  │   Collector  │  │    Filter    │  │   Download Loop        │  │
│  │ (API fetch)  │  │ (artist/album│  │ (per-item retry +      │  │
│  │              │  │  filter, new-│  │  progress + delay)     │  │
│  │              │  │  only check) │  │                        │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬─────────────┘  │
│         │                 │                     │                │
├─────────┴─────────────────┴─────────────────────┴────────────────┤
│                       Service Layer                              │
│  ┌─────────────────────┐          ┌──────────────────────────┐   │
│  │   StateManager      │          │   Downloader             │   │
│  │  read/write/update  │          │  yt-dlp subprocess       │   │
│  │  state JSON file    │          │  + retry + capture       │   │
│  └─────────────────────┘          └──────────────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                       Storage Layer                              │
│  ┌──────────────────┐    ┌──────────────┐    ┌───────────────┐   │
│  │  State JSON file │    │  Bandcamp    │    │  Local disk   │   │
│  │  ~/.bcdl/<user>  │    │  HTTP API    │    │  (yt-dlp out) │   │
│  └──────────────────┘    └──────────────┘    └───────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `main()` / CLI Layer | Parse args, validate, route to export or download workflow, report summary | All components |
| Collector (`get_page_data`, `get_all_collection_items`) | HTTP fetch of full Bandcamp collection via scrape + paginated API | Bandcamp HTTP, returns items list |
| Filter | Apply `--artist` / `--album` filters; apply incremental logic (skip already-downloaded) | StateManager (reads), receives items list |
| Download Loop | Iterate filtered items, call Downloader per item, apply delay, accumulate results | Downloader, StateManager (writes), Progress display |
| `StateManager` | Read/write/query persistent state file; mark items downloaded; check if item is known | State JSON file on disk |
| `Downloader` (`download_item`) | Invoke yt-dlp subprocess with retry on transient errors; capture stdout/stderr | yt-dlp subprocess |
| Progress display | Print per-item status, running counts, final summary | Receives signals from Download Loop |

## Recommended Project Structure

The project can stay as a single module (`bcdl.py`) for now. The new features map cleanly to helper functions and a `StateManager` class added to that file. A package layout (`src/bcdl/`) is only warranted if the file exceeds ~500 lines or team size grows.

**Preferred: augmented single-module (stay at `bcdl.py`)**

```
bcdl/
├── bcdl.py                   # All logic: CLI, collection, state, download
├── pyproject.toml
├── tests/
│   ├── conftest.py
│   ├── test_bcdl.py          # Existing tests (stay working)
│   └── test_state.py         # New tests for StateManager
└── .planning/
```

**Alternative: package layout (if file grows beyond ~500 lines)**

```
bcdl/
├── src/
│   └── bcdl/
│       ├── __init__.py       # Re-exports main() for entry point
│       ├── cli.py            # argparse + main()
│       ├── collector.py      # get_page_data, get_all_collection_items
│       ├── state.py          # StateManager class
│       ├── downloader.py     # download_item + retry logic
│       └── progress.py       # progress display helpers
├── pyproject.toml            # entry_point: "bcdl = bcdl.cli:main"
└── tests/
    ├── conftest.py
    ├── test_collector.py
    ├── test_state.py
    └── test_downloader.py
```

### Structure Rationale

- **Single-module first:** Existing tests import `bcdl` directly (`import bcdl`). Staying single-file preserves this without test changes. The logical separation already exists via named functions.
- **StateManager as class:** The only new abstraction that benefits from class encapsulation is state management — it has mutable state (the in-memory cache) and multiple methods. Everything else stays as functions.
- **Package layout deferred:** Move to `src/bcdl/` only when `bcdl.py` passes 500 lines or when separate contributors need ownership of separate modules.

## Architectural Patterns

### Pattern 1: StateManager — JSON file with atomic writes

**What:** A class that owns a JSON file at `~/.bcdl/{username}.json`. Tracks which items have been successfully downloaded, keyed by a stable item identifier (URL or `tralbum_id`). In-memory dict is loaded once at startup and flushed after each successful download.

**When to use:** Any tool that needs resume-safe progress tracking across interrupted runs.

**Trade-offs:**
- Pro: Simple to implement, human-readable, debuggable, no database dependency
- Pro: Works correctly even if the download output directory changes
- Con: No concurrent access safety (single-user CLI, not an issue here)
- Con: State file diverges from disk if user manually deletes downloaded files (acceptable — state-file is source of truth for "was downloaded", not "is present on disk")

**Key design decisions:**
- Key items by URL (stable, already available from collection API)
- Store timestamps and item metadata for future audit/display
- Write atomically: write to `.tmp` then `os.replace()` to avoid corruption on interrupt

**Example state file structure:**

```json
{
  "version": 1,
  "username": "alice",
  "downloads": {
    "https://artistone.bandcamp.com/album/album-one": {
      "status": "downloaded",
      "downloaded_at": "2026-03-19T10:00:00Z",
      "artist": "Artist One",
      "title": "Album One"
    },
    "https://artisttwo.bandcamp.com/track/track-two": {
      "status": "failed",
      "last_attempt": "2026-03-19T10:05:00Z",
      "artist": "Artist Two",
      "title": "Track Two"
    }
  }
}
```

**State file location:** `~/.bcdl/{username}.json`

Rationale: per-username file means multiple users can be tracked independently; `~/.bcdl/` is a conventional XDG-style location for tool data in the user's home directory. Alternatively configurable via `--state-file FILE` flag for power users.

### Pattern 2: Retry with exponential backoff

**What:** Wrap the `subprocess.run()` call for yt-dlp in a retry loop. Detect transient failures by return code (non-zero) and optionally by captured stderr content (HTTP 429, connection reset). Apply exponential backoff with jitter between attempts.

**When to use:** Any network operation that can fail transiently. For yt-dlp specifically: HTTP 429 (rate limit), 5xx server errors, timeout, and connection errors all warrant retry.

**Trade-offs:**
- Pro: Makes downloads resilient to flaky connections without user intervention
- Con: Longer total runtime when transient failures occur
- Con: yt-dlp already retries some errors internally — need to check `--retries` yt-dlp flag to avoid double-retrying at both layers

**Recommended approach:**
- Pass `--retries 3` to yt-dlp for yt-dlp-level retries (format errors, fragment errors)
- Add one outer retry loop in `download_item()` for subprocess-level failures (yt-dlp crashes, OS errors)
- Max 2 outer retries with 5s → 15s backoff
- Use `subprocess.run(capture_output=True)` to capture stderr and surface it on final failure

### Pattern 3: Pre-filter before download loop (incremental sync + targeted download)

**What:** After collecting all items from the API, pass them through a filter step before the download loop begins. The filter layer is a pure function: takes `(items, state, args)` and returns a filtered list. Two filters compose: the "already downloaded" check (incremental sync) and the artist/album substring match (targeted download).

**When to use:** Any time there are multiple criteria for deciding whether to process an item.

**Trade-offs:**
- Pro: Download loop stays simple — it sees only items it should process
- Pro: Filters are independently testable as pure functions
- Pro: User sees an accurate "N items to download" count upfront
- Con: Entire collection must be fetched from API before filtering can begin (unavoidable — Bandcamp API has no server-side filter)

**Data flow:**

```
all_items (from API)
    ↓
filter_new_only(items, state)        ← incremental: drop already-downloaded
    ↓
filter_by_target(items, args)        ← targeted: keep only artist/album matches
    ↓
filtered_items (passed to loop)
```

## Data Flow

### Full Download Run (first time)

```
bcdl alice --cookies cookies.txt
    ↓
main() parses args
    ↓
StateManager.load("alice")           → creates ~/.bcdl/alice.json if missing
    ↓
get_all_collection_items("alice")    → HTTP to bandcamp.com (scrape + paginate)
    ↓
filter_new_only(items, state)        → all pass (no prior state)
    ↓
filter_by_target(items, args)        → all pass (no --artist/--album set)
    ↓
print "Downloading N items"
    ↓
for item in filtered_items:
    download_item(item, ...)         → yt-dlp subprocess (with retry)
    StateManager.mark_downloaded(url)  → atomic write to JSON
    print progress
    sleep(delay)
    ↓
print summary
```

### Incremental Sync (subsequent run)

```
bcdl alice --cookies cookies.txt
    ↓
StateManager.load("alice")           → loads existing ~/.bcdl/alice.json
    ↓
get_all_collection_items("alice")    → HTTP fetch (always fresh from API)
    ↓
filter_new_only(items, state)        → drops URLs already in state["downloads"]
    ↓
print "N new items to download (M already downloaded)"
    ↓
[same download loop as above, only for new items]
```

### Targeted Download

```
bcdl alice --artist "Floating Points" --cookies cookies.txt
    ↓
[fetch all, filter_new_only, then...]
    ↓
filter_by_target(items, args)        → keeps only items where band_name matches
    ↓
[download loop for matched new items only]
```

### State Management

```
StateManager (in-memory dict backed by JSON file)
    │
    ├── load(username) → reads ~/.bcdl/{username}.json → populates self._data
    │
    ├── is_downloaded(url) → checks self._data["downloads"][url]["status"]
    │
    ├── mark_downloaded(url, item) → updates dict + atomic file write
    │
    ├── mark_failed(url, item) → updates dict + atomic file write
    │
    └── downloaded_urls() → returns set of URLs with status=="downloaded"
```

**Atomic write pattern:**

```python
import os, json, pathlib

def _save(self) -> None:
    tmp = self._path.with_suffix(".tmp")
    tmp.write_text(json.dumps(self._data, indent=2), encoding="utf-8")
    os.replace(tmp, self._path)   # atomic on POSIX + Windows
```

## Build Order

Features have dependencies. Build in this order:

1. **StateManager class** — everything else depends on it. Write and test it in isolation first. It has no dependencies on other new features.

2. **Retry logic in `download_item()`** — depends only on the existing subprocess call. Isolated change to one function. Add `capture_output=True` here to stop flooding terminal.

3. **Filter functions** (`filter_new_only`, `filter_by_target`) — pure functions, depend on StateManager's `downloaded_urls()`. Independently testable.

4. **Wire filters + StateManager into `main()`** — now `main()` gains incremental sync and targeted download. Depends on 1 + 3.

5. **Progress display** — cosmetic layer, slot in once the loop logic is stable. No other features depend on it.

6. **`--format` flag** — single-line addition to `download_item()`, pass-through to yt-dlp. Can be done in any phase since it's additive.

7. **Packaging / CI** — depends on all features being stable.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Bandcamp collection API | HTTP GET (scrape) + POST (paginate) via `requests` | Unofficial API — no auth, relies on HTML structure and JSON blob in `#pagedata` div. Fragile: HTML changes can break scraping. |
| yt-dlp | subprocess invocation | User must install separately. Use `capture_output=True` to suppress noise. Pass `--retries 3 --fragment-retries 3` for built-in retry. Pass `--format` from CLI arg. |
| State JSON file | `pathlib.Path` read/write | One file per username at `~/.bcdl/{username}.json`. Use atomic write (`os.replace`) to avoid corruption. |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| `main()` ↔ `StateManager` | Direct method calls | StateManager is instantiated once in `main()`, passed to filter functions and download loop |
| `main()` ↔ filter functions | Pure function calls — receive items list + state + args, return filtered list | No side effects; easy to unit test |
| `main()` ↔ `download_item()` | Direct function call | `download_item()` remains a function (not a method); receives all it needs as arguments |
| `download_item()` ↔ yt-dlp | `subprocess.run(capture_output=True)` | Capture stdout/stderr to prevent terminal flood; surface stderr on failure |

## Anti-Patterns

### Anti-Pattern 1: Scanning disk to detect already-downloaded items

**What people do:** Check whether a file exists on disk to determine if an item was already downloaded (e.g., look for a directory named after the artist/album).

**Why it's wrong:** yt-dlp's output path format is configurable and may not match what the detection logic expects. File can be renamed, moved, or partially downloaded. Logic becomes coupled to yt-dlp's naming conventions, which vary by format and template.

**Do this instead:** Track downloads in the state JSON file, keyed by URL. State is set after confirmed yt-dlp success (returncode == 0). Source of truth is the state file, not the disk.

### Anti-Pattern 2: Writing state only at the end of a full run

**What people do:** Accumulate all successful items in memory and write the state file once at the end of `main()`.

**Why it's wrong:** Any interruption (Ctrl+C, crash, network loss) loses all progress tracking. On resume, items that were successfully downloaded get downloaded again.

**Do this instead:** Call `state.mark_downloaded(url)` immediately after each successful yt-dlp call and before the inter-item delay. The atomic write costs ~1ms per item — negligible.

### Anti-Pattern 3: Growing `main()` with all new logic inline

**What people do:** Add incremental-sync checking, retry loops, filter conditions, and progress logic directly into `main()` as the function grows.

**Why it's wrong:** `main()` becomes untestable (the existing tests already skip it). The retry, filter, and state logic all need unit tests that require mocking; inline code can't be tested independently.

**Do this instead:** Extract each concern into a named function or class. Keep `main()` as a thin coordinator: parse args → load state → fetch → filter → loop → summarize.

### Anti-Pattern 4: Using a database for state

**What people do:** Reach for SQLite (or similar) to store download state.

**Why it's wrong:** This is a single-user CLI tool with sequential access. SQLite adds a dependency, makes the state file non-human-readable, and complicates debugging. A JSON file is sufficient for collections up to tens of thousands of items.

**Do this instead:** JSON file with atomic writes. If the collection grows to 100k+ items and lookup performance becomes an issue, convert the `downloads` dict to use a flat set (URLs only) and separate metadata file.

## Scaling Considerations

This is a single-user CLI. "Scaling" means handling large Bandcamp collections (100–10,000 items).

| Scale | Architecture Adjustment |
|-------|--------------------------|
| 0-500 items | Current approach works. Sequential download with delay. |
| 500-5,000 items | State file lookup stays O(1) (dict). No architectural change needed. |
| 5,000+ items | State file may reach 1-5MB — still fine for JSON. Consider `--limit N` flag to cap runs. |
| Concurrent downloads | Out of scope. yt-dlp itself parallelizes internally. Adding outer concurrency risks rate-limiting. |

## Sources

- Codebase analysis: `/Users/jolilius/home/src/bcdl/bcdl.py` (186 lines, reviewed 2026-03-19)
- Codebase architecture: `.planning/codebase/ARCHITECTURE.md` (reviewed 2026-03-19)
- Project requirements: `.planning/PROJECT.md` (reviewed 2026-03-19)
- Python stdlib: `pathlib`, `os.replace()` for atomic writes — standard pattern, HIGH confidence
- yt-dlp flags `--retries`, `--fragment-retries`, `capture_output` — standard subprocess pattern, HIGH confidence

---
*Architecture research for: Python CLI downloader (bcdl)*
*Researched: 2026-03-19*
