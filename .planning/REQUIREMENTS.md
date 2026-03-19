# Requirements: bcdl — Bandcamp Collection Downloader

**Defined:** 2026-03-19
**Core Value:** Any Bandcamp buyer can sync their full collection with one command, picking up where they left off if interrupted.

## v1 Requirements

### Reliability

- [ ] **RELY-01**: Tool retries failed requests automatically on transient failures (HTTP 429, 5xx, timeouts) without user intervention

### Resume & State

- [ ] **RESM-01**: Tool tracks downloaded items in a local state file so already-downloaded items are skipped on subsequent runs

### Download Control

- [ ] **DCTL-01**: User can specify audio format via `--format` flag (e.g. `flac`, `mp3`) passed through to yt-dlp

### Documentation

- [ ] **DOCS-01**: README documents all flags with usage examples and install instructions clear enough for a non-developer Bandcamp user

## v2 Requirements

### Reliability

- **RELY-02**: yt-dlp output is captured and suppressed; only clean per-item status shown to user
- **RELY-03**: JSON decode errors from malformed Bandcamp responses produce a friendly, actionable error message
- **RELY-04**: Retry count and backoff delay are configurable via CLI flags

### Resume & State

- **RESM-02**: Incremental sync mode — only downloads items not present in state file (new purchases since last run)
- **RESM-03**: User can override default state file location via `--state-file FILE` flag

### Download Control

- **DCTL-02**: User can set download destination directory via `--output-dir` flag
- **DCTL-03**: User can filter collection by artist or album name to download only matching items
- **DCTL-04**: `--dry-run` flag shows what would be downloaded without performing any downloads
- **DCTL-05**: Failed items are listed in a summary at the end of each run

### Distribution

- **DIST-01**: Tool is installable via `pip install bcdl` / `pipx install bcdl`
- **DIST-02**: GitHub Actions CI runs tests automatically on push

## Out of Scope

| Feature | Reason |
|---------|--------|
| GUI or web interface | CLI-first tool; out of scope for v1+ |
| Parallel downloads | Bandcamp rate-limits aggressively; sequential + delay is correct tradeoff |
| Wishlisted / followed items | Only purchased collection supported |
| Bandcamp login / OAuth | Auth via user-supplied cookies file only |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| RELY-01 | Phase ? | Pending |
| RESM-01 | Phase ? | Pending |
| DCTL-01 | Phase ? | Pending |
| DOCS-01 | Phase ? | Pending |

**Coverage:**
- v1 requirements: 4 total
- Mapped to phases: 0
- Unmapped: 4 ⚠️

---
*Requirements defined: 2026-03-19*
*Last updated: 2026-03-19 after initial definition*
