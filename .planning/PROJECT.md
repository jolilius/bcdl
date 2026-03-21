# bcdl — Bandcamp Collection Downloader

## What This Is

A CLI tool that lets any Bandcamp buyer download their entire purchased collection with a single command. Built on top of yt-dlp, it handles pagination through large collections, retries transient failures automatically, supports resuming interrupted runs, and is installable via `pipx install bcdl`.

## Core Value

Any Bandcamp buyer can sync their full collection with one command, picking up exactly where they left off if interrupted.

## Requirements

### Validated

- ✓ Fetch all collection items via Bandcamp's API (HTML scrape + paginated REST) — existing
- ✓ Download items via yt-dlp subprocess — existing
- ✓ Export collection to CSV — existing
- ✓ Configurable delay between downloads (`--delay`) — existing
- ✓ Cookies file support for authenticated downloads (`--cookies`) — existing
- ✓ Resume interrupted downloads using a local state file (skip already-downloaded items) — v1.0
- ✓ Auto-retry on transient failures (HTTP 429, 5xx, timeouts) with exponential backoff — v1.0
- ✓ yt-dlp output captured and suppressed; clean per-item status lines shown instead — v1.0
- ✓ Audio format selection via `--format` flag (flac, mp3, wav, aac, opus) — v1.0
- ✓ README documents all flags with usage examples for non-developer Bandcamp users — v1.0
- ✓ Installable via `pipx install bcdl` — v1.0
- ✓ GitHub Actions CI runs tests on push — v1.0

### Active

- [ ] Incremental sync — only download items not previously downloaded
- [ ] Targeted download — filter by artist or album name
- [ ] Output directory selection via `--output-dir` flag
- [ ] Retry count and backoff delay configurable via CLI flags
- [ ] State file location override via `--state-file` flag
- [ ] JSON decode errors from malformed Bandcamp responses produce friendly, actionable error

### Out of Scope

- GUI or web interface — CLI-first tool
- Parallel downloads — Bandcamp rate-limits aggressively; sequential + delay is correct tradeoff
- Downloading wishlisted or followed items — only purchased collection
- Bandcamp login / OAuth — relies on user-provided cookies file for auth

## Context

**Shipped v1.0 (2026-03-21):**
- 370 LOC Python (bcdl.py), 694 LOC tests (65 tests, 100% passing)
- Tech stack: Python 3.12+, yt-dlp, uv, pytest, hatchling, GitHub Actions
- Installable wheel at `dist/bcdl-0.1.0-py3-none-any.whl`; entry point `bcdl = bcdl:main`

**Known tech debt:**
- `download_item` function in bcdl.py is dead code (unreachable from main(); tested but not in production call graph)
- All `*-VALIDATION.md` Nyquist files remain in `draft` state

## Constraints

- **Runtime:** Python 3.12+ (uses modern union type syntax)
- **External dep:** yt-dlp must be installed by user (not bundled); ffmpeg required for `--format` flag
- **API:** Bandcamp API is unofficial/undocumented — scraping is inherently fragile

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| State file for resume tracking | Simpler than disk scanning, works even if download dir changes | ✓ Implemented (v1.0) |
| yt-dlp as download backend | Handles auth, format selection, retries at download layer | ✓ Good |
| uv for project management | Modern, fast, already in use | ✓ Good |
| State keyed by `str(sale_item_id)` | Stable numeric ID; items missing it download every time, never get a state entry | ✓ Correct |
| Atomic writes via `NamedTemporaryFile + os.replace` | `dir=path.parent` mandatory to avoid cross-filesystem failure | ✓ Correct |
| PERMANENT_PATTERNS checked before TRANSIENT_PATTERNS | Mixed-signal stderr (403 + 429) returns "permanent" — fail fast | ✓ Correct |
| `download_with_retry` replaces `download_item` in main() | Clean separation of retry logic from subprocess invocation | ✓ Good — but `download_item` not removed (tech debt) |
| `pipx install` as primary install path | Non-developer users can install without understanding venvs | ✓ Confirmed by smoke test |
| `audio_format` parameter (not `format`) | Avoids shadowing Python built-in | ✓ Good |
| `dist/` excluded from git | Wheel is a build artifact; `uv build` regenerates on demand | ✓ Correct |

---
*Last updated: 2026-03-21 after v1.0 milestone*
