# bcdl — Bandcamp Collection Downloader

## What This Is

A CLI tool that lets any Bandcamp buyer download their entire purchased collection with a single command. Built on top of yt-dlp, it handles pagination through large collections, supports resuming interrupted runs, and is designed to be installable via pip/pipx and distributed publicly on GitHub.

## Core Value

Any Bandcamp buyer can sync their full collection — or just new purchases — with one command, picking up exactly where they left off if interrupted.

## Requirements

### Validated

- ✓ Fetch all collection items via Bandcamp's API (HTML scrape + paginated REST) — existing
- ✓ Download items via yt-dlp subprocess — existing
- ✓ Export collection to CSV — existing
- ✓ Configurable delay between downloads (`--delay`) — existing
- ✓ Cookies file support for authenticated downloads (`--cookies`) — existing

### Active

- [ ] Resume interrupted downloads using a local state file (skip already-downloaded items)
- [ ] Incremental sync — only download items not previously downloaded
- [ ] Targeted download — filter by artist or album name without downloading entire collection
- [ ] Format selection via `--format` flag passed through to yt-dlp
- [ ] Rich progress display — per-item status, success/fail summary, running count
- [ ] Retry logic for transient network failures (HTTP 429, 5xx, timeouts)
- [ ] Capture and surface yt-dlp errors clearly instead of flooding terminal
- [ ] Installable via `pip install bcdl` / `pipx install bcdl`
- [ ] GitHub Actions CI — runs tests on push
- [ ] Polished README — install instructions, usage examples, all flags documented

### Out of Scope

- GUI or web interface — CLI-first tool
- Downloading wishlisted or followed items — only purchased collection
- Bandcamp login / OAuth — relies on user-provided cookies file for auth

## Context

- Existing codebase: `bcdl.py` (186 lines), functional but not production-hardened
- Known concerns: no retry logic, no resume, subprocess errors not captured, `main()` untested
- Currently managed with uv; entry point already defined in `pyproject.toml`
- Tests use pytest + unittest.mock; 14 unit tests covering core functions (not `main()`)

## Constraints

- **Runtime**: Python 3.12+ (uses modern union type syntax)
- **External dep**: yt-dlp must be installed by user (not bundled)
- **API**: Bandcamp API is unofficial/undocumented — scraping is inherently fragile

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| State file for resume tracking | Simpler than disk scanning, works even if download dir changes | — Pending |
| yt-dlp as download backend | Handles auth, format selection, retries at download layer | ✓ Good |
| uv for project management | Modern, fast, already in use | ✓ Good |

---
*Last updated: 2026-03-19 after initialization*
