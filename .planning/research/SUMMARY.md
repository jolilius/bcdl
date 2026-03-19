# Project Research Summary

**Project:** bcdl — Bandcamp Collection Downloader
**Domain:** Python CLI batch downloader (PyPI-distributable)
**Researched:** 2026-03-19
**Confidence:** MEDIUM (stack/architecture HIGH from codebase inspection; features MEDIUM from competitor analysis)

## Executive Summary

bcdl is a single-command Python CLI tool that downloads a user's purchased Bandcamp collection via yt-dlp. The current implementation is functional but lacks every feature that competing tools (Ezwen/bandcamp-collection-downloader, easlice/bandcamp-downloader, bandsnatch) treat as table stakes: resume after interruption, format selection, configurable output directory, suppressed subprocess output, and retry on transient failures. The recommended approach is to add these features incrementally to the existing single-file architecture (`bcdl.py`) rather than restructuring — the codebase is small enough that modular extraction would be premature.

The highest-leverage change is introducing a `StateManager` class backed by a JSON file at `~/.bcdl/{username}.json`. This single addition unlocks both resume-after-interruption and incremental sync (only download new purchases). All other v1 features — retry logic, format selection, output directory, suppressed yt-dlp output, and a structured failure summary — are low-complexity additions once the state file foundation is in place. Two libraries should be added: `rich` (for progress display that doesn't corrupt under subprocess output) and `tenacity` (for retry with exponential backoff). Everything else in the current stack is correct.

The key risks are technical: state file corruption on interrupted writes (use atomic `os.replace()` pattern — mandatory, not optional), retry logic that retries permanent failures like 404s (filter by error type), and yt-dlp stdout flooding the progress display (requires shipping `capture_output=True` and the Rich progress layer together). An additional pre-publish risk is PyPI name collision — `bcdl` is short enough that another project may have claimed it; verify before any release.

## Key Findings

### Recommended Stack

The existing stack (Python 3.12+, uv, hatchling, requests, beautifulsoup4, argparse) is correct and should not change. Two production dependencies need adding: `rich >=13,<14` for terminal progress display and `tenacity >=8.2,<9` for retry logic. `rich` is the right choice over `tqdm` because it handles both a running progress bar and per-item status lines without corruption — the exact pattern bcdl needs. `tenacity` is preferred over a manual retry loop because it cleanly separates retry conditions (retry on 429/5xx/timeout, not on 404) via composable predicates.

State tracking should use a plain JSON file (`~/.bcdl/{username}.json`), not SQLite. The data model is a flat mapping of item URLs to download status — JSON is human-readable, debuggable, and fully adequate for collections up to 10,000+ items. State must be written atomically per item (write to `.tmp`, then `os.replace()`) to prevent corruption on Ctrl-C.

**Core technologies:**
- Python 3.12+: runtime — already required, no change
- uv: project manager — fastest resolver, handles virtualenvs, already in use
- hatchling: PyPI build backend — PEP 517 compliant, entry points work correctly
- requests: HTTP client — correct for Bandcamp's sequential API calls (no async needed)
- beautifulsoup4: HTML parsing — correct for scraping the embedded JSON blob
- rich (NEW): progress display and console output — handles concurrent progress bar + per-item log lines
- tenacity (NEW): retry with exponential backoff — composable retry predicates, actively maintained
- argparse: CLI argument parsing — keep as-is; no subcommands needed, migration to click/typer adds zero value

### Expected Features

Every competitor implements resume, format selection, output directory, and retry. These are not differentiators — they are the minimum bar for a credible tool. bcdl currently has none of them, which puts it below the baseline.

**Must have (table stakes for v1):**
- Resume / skip already-downloaded — users with 300+ item collections cannot use a tool that requires restarting from scratch on interruption
- Retry on transient failures — HTTP 429 and 5xx are common against Bandcamp's API; a single abort is unacceptable
- Format selection (`--format`) — users who need FLAC cannot use a tool that doesn't expose this
- Suppressed yt-dlp output with clear per-item status lines — stdout flooding is the most visible UX complaint across all competitors
- Final summary with failed item names (not just count) — users need actionable output when something goes wrong
- Configurable output directory (`--output`) — currently hardcoded to cwd
- Helpful error on missing yt-dlp — converts a cryptic `FileNotFoundError` into an actionable install message

**Should have (v1.x, post-validation):**
- Incremental sync — only download new purchases since last run; builds on the state file
- Filter by artist/album name (`--filter`) — targeted downloads for large collections
- Dry-run mode (`--dry-run`) — preview what would be downloaded; low effort, high value
- Date-range filtering (`--since DATE`) — complements incremental sync for date-based workflows
- Structured failure log (`--failed-log FILE`) — machine-readable list of failures for retry scripts

**Defer (v2+):**
- yt-dlp passthrough args (`--yt-dlp-args`) — useful but adds surface area; defer until core flags are stable
- Environment variable configuration — useful for CI automation but adds documentation burden
- Parallel downloads — all competitors offer this but Bandcamp rate-limits concurrent requests aggressively; the complexity-to-benefit ratio is poor for a sequential-first tool

### Architecture Approach

The architecture should stay as a single module (`bcdl.py`) with the new logic organized into named functions and one class (`StateManager`). The only abstraction that benefits from class encapsulation is state management — it has mutable state and multiple methods. Everything else (collector, filter functions, download loop) stays as functions. This preserves compatibility with the existing tests. A package layout (`src/bcdl/`) is deferred until the file exceeds ~500 lines.

The build order within any implementation phase should follow the dependency graph: `StateManager` first (everything depends on it), then retry logic in `download_item()`, then filter functions (pure, depend on state), then wire filters into `main()`, then add the Rich progress layer last (cosmetic, no other features depend on it).

**Major components:**
1. CLI Layer (`main()`) — argparse, arg validation, workflow routing, exit codes
2. Collector (`get_page_data`, `get_all_collection_items`) — HTTP fetch and pagination of Bandcamp collection
3. Filter functions (`filter_new_only`, `filter_by_target`) — pure functions that decide which items to process
4. `StateManager` class — read/write/query persistent JSON state file; atomic writes per item
5. `Downloader` (`download_item`) — invoke yt-dlp subprocess with retry; capture output
6. Progress display — Rich-based per-item status and running summary (slots in after loop logic is stable)

### Critical Pitfalls

1. **State file corruption on interrupted write** — write atomically using `os.replace()` on a `.tmp` file; wrap reads in `try/except json.JSONDecodeError`; never silently swallow a corrupt state file. This is mandatory from the first day state tracking is introduced.

2. **State keyed on mutable fields (title/artist name)** — key state on the stable numeric item ID from Bandcamp's API (`tralbum_id` or the key from `item_cache.collection`), not on title strings. A title change on Bandcamp causes re-downloads if keyed on title. This decision cannot be corrected without invalidating all existing state files.

3. **yt-dlp stdout flooding Rich progress display** — `subprocess.run(capture_output=True)` and the Rich progress layer must ship together. Adding Rich without capturing subprocess output produces garbled terminal output. These are a single unit of work, not two separate changes.

4. **Retry logic that retries non-retryable errors** — only retry on `ConnectionError`, `Timeout`, HTTP 429, and HTTP 5xx. Never retry 404 (item deleted), 401/403 (auth failure), or malformed JSON. Use tenacity's `retry_if_exception` to enforce this; never use a blanket `except Exception`.

5. **Hatchling may exclude `bcdl.py` from the wheel** — a top-level `.py` file is less obviously included than a package directory. Verify with `unzip -l dist/*.whl | grep bcdl.py` before any PyPI publish. If missing, add `[tool.hatch.build.targets.wheel] include = ["bcdl.py"]` to `pyproject.toml`.

## Implications for Roadmap

Based on research, the dependency graph between features drives the phase order. `StateManager` is the foundation; nothing else can be built correctly without it. Progress display and subprocess capture are tightly coupled and must ship together. PyPI packaging is a gate on public release, not a feature phase.

### Phase 1: Foundation — Error Hardening and State Infrastructure

**Rationale:** Two things are true simultaneously: (a) the existing code has reliability bugs that exist today (garbled Bandcamp DOM errors, missing yt-dlp check, no exit code on failure), and (b) the `StateManager` is the dependency for every other v1 feature. Fixing existing reliability issues while building the state foundation means Phase 1 delivers a more robust tool before any new features are added.

**Delivers:** A correct, reliable baseline — actionable errors, proper exit codes, and a working StateManager class with atomic write and stable key selection.

**Addresses:**
- Helpful error on missing yt-dlp (table stakes)
- Final summary with exit code 1 on failure (table stakes)
- Bandcamp DOM change producing confusing error (existing bug from CONCERNS.md)

**Avoids:**
- State keyed on mutable title fields (must be correct from first commit)
- State file corruption on interrupted write (atomic write pattern from day one)
- State file in wrong default location (XDG-compliant `~/.bcdl/{username}.json` from day one)

### Phase 2: Download Reliability — Retry, Capture, and Progress Display

**Rationale:** Once the state infrastructure exists, the next highest-value changes are retry logic (makes downloads resilient to Bandcamp's frequent 429s) and subprocess output capture with progress display. These must ship together — capturing yt-dlp output without replacing it with meaningful feedback would be a regression in UX.

**Delivers:** A tool that handles transient failures without user intervention and shows clear per-item status instead of yt-dlp's verbose output.

**Uses:**
- `tenacity` for retry with exponential backoff and per-error-type retry predicates
- `rich` for `Progress` bar, per-item `Console.log()` lines, and running success/fail counts

**Implements:** Downloader component with retry + progress display layer

**Avoids:**
- Blanket retry on permanent errors (tenacity's `retry_if_exception` enforces type filtering)
- yt-dlp stdout flooding Rich display (both changes ship in the same phase)

### Phase 3: Core Feature Set — Format, Output Directory, Resume

**Rationale:** With reliable downloads and state tracking in place, this phase completes the v1 feature set. Format selection and output directory are low-complexity CLI flag additions. Resume (skip already-downloaded) is the state file put to use — the hard work was done in Phase 1.

**Delivers:** A fully-featured v1 tool that matches competitor table stakes: users can choose format, choose where files land, and resume interrupted runs without re-downloading.

**Addresses:**
- Format selection (`--format` mapped to yt-dlp format strings, not passed verbatim)
- Configurable output directory (`--output`)
- Resume / skip already-downloaded (wires `StateManager.is_downloaded()` into the download loop)

**Avoids:**
- Format string passed verbatim to yt-dlp (map simple names like `flac`, `mp3` to yt-dlp syntax)

### Phase 4: Power Features — Incremental Sync and Targeting

**Rationale:** These features extend the state foundation to power-user workflows. Incremental sync (only download new purchases) requires the state file from Phase 1 to work correctly. Filter-by-artist and dry-run mode are independent but frequently used together.

**Delivers:** Incremental sync, artist/album filtering, dry-run preview, date-range filtering, and structured failure log. The tool is now suitable for automated/scheduled use.

**Addresses:**
- Incremental sync (requires state file and pagination order assumption — verify Bandcamp's newest-first ordering before relying on early-exit optimization)
- Filter by artist/album (`--filter`, using `fnmatch`)
- Dry-run mode (`--dry-run`)
- Date-range filtering (`--since DATE`)
- Structured failure log (`--failed-log FILE`)

### Phase 5: Packaging and Release

**Rationale:** PyPI publish is a gate, not a feature. It requires a name availability check, wheel content verification, and end-to-end install testing from the wheel (not editable install). This phase is isolated to release infrastructure.

**Delivers:** A working PyPI package installable via `pipx install bcdl`.

**Avoids:**
- PyPI name collision (verify `pip index versions bcdl` before building)
- Hatchling excluding `bcdl.py` from wheel (verify with `unzip -l dist/*.whl | grep bcdl.py`)
- Publishing without testing entry point from wheel (`pipx install dist/*.whl && bcdl --help`)

### Phase Ordering Rationale

- Phase 1 before everything else because the state key decision (stable ID vs mutable title) is irreversible — it must be correct from first commit or all state files become invalid.
- Phase 2 before Phase 3 because resume requires confident download tracking, which requires reliable download outcomes (retry + captured output).
- Phase 3 before Phase 4 because incremental sync builds on the same state infrastructure as resume; both are in the same state model.
- Phase 5 last because it validates the complete feature set.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 4 (Incremental sync):** The early-exit optimization (stop paginating once a known item is seen) assumes Bandcamp returns collection items newest-first. This assumption must be verified against the actual API before implementation — fall back to full-fetch + state deduplication if not guaranteed.
- **Phase 5 (Packaging):** PyPI name `bcdl` availability is unknown — check before beginning this phase. If taken, the package name and README must be updated before release.

Phases with standard patterns (skip research-phase):
- **Phase 1 (StateManager):** Atomic JSON file pattern is well-established; no research needed.
- **Phase 2 (Retry + Progress):** `tenacity` and `rich` APIs are stable and well-documented.
- **Phase 3 (Format/Output/Resume):** All are argparse additions and state file reads; standard patterns throughout.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Based on direct codebase inspection (uv.lock, pyproject.toml, bcdl.py) and training knowledge for rich/tenacity. Cannot verify exact latest versions without network access; version ranges are conservative. |
| Features | MEDIUM | Based on competitor README and issue tracker analysis via WebFetch. No direct user survey. Feature expectations are consistent across all three major competitors. |
| Architecture | HIGH | Based on direct inspection of existing 186-line codebase and established Python CLI patterns. Component boundaries are clear and the build order follows a deterministic dependency graph. |
| Pitfalls | HIGH | Based on codebase inspection and CONCERNS.md. Most pitfalls are well-documented failure modes for this class of tool (CLI downloaders with state tracking and subprocess orchestration). |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Bandcamp pagination order:** Incremental sync's early-exit optimization assumes newest-first ordering. Verify by inspecting a multi-page API response during Phase 4 planning before committing to implementation strategy.
- **PyPI name availability:** `bcdl` name status on PyPI is unknown. Check before Phase 5. If taken, decide on alternative name early (rename affects pyproject.toml, README, and any external references).
- **yt-dlp format strings for Bandcamp:** The mapping from user-friendly format names (`flac`, `mp3`) to yt-dlp format selector strings that work specifically with Bandcamp should be verified against a live download during Phase 3. Bandcamp's yt-dlp extractor may handle format selection differently than generic extractors.

## Sources

### Primary (HIGH confidence)
- `bcdl.py` (186 lines, direct read) — existing implementation, subprocess pattern, argparse usage
- `pyproject.toml` (direct read) — hatchling build backend, entry point, Python version constraint
- `uv.lock` (direct read) — confirmed beautifulsoup4 4.14.3, certifi 2026.2.25, exact locked versions
- `tests/test_bcdl.py` (direct read) — test coverage scope and existing test patterns
- `.planning/codebase/CONCERNS.md` (direct read) — existing technical debt inventory
- Python stdlib docs — `os.replace()` atomic write, `shutil.which()`, `pathlib.Path`

### Secondary (MEDIUM confidence)
- Ezwen/bandcamp-collection-downloader README and issues — feature expectations, competitor patterns
- easlice/bandcamp-downloader README and issues — date filtering, browser cookie auto-detect, retry patterns
- bandsnatch README and issues — Rust implementation, parallel download approach
- Training knowledge (cutoff Aug 2025) — rich vs tqdm comparison, tenacity API, pipx distribution pattern

### Tertiary (LOW confidence)
- Bandcamp's pagination order (newest-first assumption) — inferred from collection API structure, not verified against live API

---
*Research completed: 2026-03-19*
*Ready for roadmap: yes*
