# Feature Research

**Domain:** CLI batch downloader — Bandcamp purchased collection
**Researched:** 2026-03-19
**Confidence:** MEDIUM (competitor READMEs via WebFetch; issue trackers; no direct user survey)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Resume / skip already-downloaded | Running twice on a large collection is unusable without it. All three major competitors implement this via cache file. | MEDIUM | State file keyed on item URL or ID; checked before invoking yt-dlp. Current bcdl has no resume. |
| Format selection (`--format`) | Bandcamp natively offers 8 formats; users choose lossless vs lossy before downloading. Every competitor exposes this flag. | LOW | Pass through to yt-dlp `--audio-format` or use Bandcamp direct download URL with format param. |
| Clear per-item progress output | Users with 300+ item collections need feedback. yt-dlp flooding stdout is the #1 UX complaint in competitor issue trackers. | LOW | Suppress yt-dlp stdout; print `[N/total] Artist — Album ... OK / FAILED` lines. |
| Final summary (success/fail counts) | Users want to know what failed at the end without scrolling. | LOW | Already partially implemented in bcdl; needs fail list with names, not just count. |
| Retry on transient failures | HTTP 429 and 5xx are common against Bandcamp's API. A single abort on a 100-item collection is unacceptable. | LOW | Exponential backoff, 3 attempts. Applies to both API pagination and yt-dlp invocations. |
| Configurable output directory (`--output`) | Users want music in ~/Music, not the cwd. All competitors provide this. | LOW | Pass `--paths` to yt-dlp or set working directory before subprocess call. |
| Cookies file authentication | Bandcamp requires auth for purchased content. Already implemented; must not regress. | LOW | Already present; ensure clear error when cookies are missing or rejected. |
| Helpful error on missing yt-dlp | yt-dlp is an external dep. If absent, current error is a cryptic `FileNotFoundError`. | LOW | Catch `FileNotFoundError` from subprocess, print actionable install instructions. |

### Differentiators (Competitive Advantage)

Features that set the product apart. Not required, but valued.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Incremental sync (new purchases only) | Users run bcdl on a schedule; they only want items added since last run. Bandcamp orders collection newest-first, enabling early exit. | MEDIUM | Track last-seen item ID or purchase date in state file. Stop paginating when reaching a known item. |
| Filter by artist / album name (`--filter`) | Users with 500+ item collections want targeted downloads without scripting. Requested in easlice issue tracker. | LOW | `fnmatch` against `band_name` or `album_title` fields before invoking yt-dlp. |
| Dry-run mode (`--dry-run`) | Power users verify what would be downloaded before running. All major competitors offer this; easlice and bandsnatch users explicitly cite it. | LOW | Print items that would be downloaded; skip yt-dlp calls. |
| yt-dlp passthrough args (`--yt-dlp-args`) | Users who know yt-dlp want to control output templates, embed thumbnails, etc. bcdl sits on top of yt-dlp so exposing this costs nothing. | LOW | Append extra args list to the yt-dlp subprocess command. |
| Structured failure log (`--failed-log FILE`) | Large collections have intermittent failures; users want a machine-readable list to retry later. | LOW | Write JSON or newline-separated URLs of failed items to file. |
| Date-range filtering (`--since DATE`) | Easlice/bandcamp-downloader offers `--download-since` and `--download-until`. Useful for "download what I bought this month." | LOW | Compare item `purchased` timestamp against provided date before processing. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Parallel / concurrent downloads | Speed. Bandcamp-collection-downloader and bandsnatch both default to 4 threads. | Bandcamp aggressively rate-limits concurrent requests. With yt-dlp as backend (which itself manages connections), parallelism adds queue complexity, retry coordination, and terminal output chaos for marginal gain. Single-collection downloads rarely take long enough to matter. | Keep sequential downloads with configurable delay. Expose `--delay 0` for power users who accept the risk. |
| Browser cookie auto-detection | Convenience — easlice detects Firefox/Chrome cookies automatically. | Requires platform-specific code paths, keyring access, browser profile discovery, and breaks between browser versions. High maintenance surface for a marginal UX gain. | Document `yt-dlp --cookies-from-browser` as the path to cookie export; keep `--cookies FILE` as the interface. |
| GUI / web interface | Accessibility for non-technical users. | Entirely outside the CLI-first value proposition. Adds massive scope. Non-technical users have the batchcamp browser extension for this. | Keep CLI, invest in a polished `--help` and README. |
| Built-in Bandcamp login (username + password) | Avoid needing to export cookies. | Bandcamp does not expose a public auth API. Scraping login forms is fragile, ToS-violating, and breaks with 2FA. Metalnem/bandcamp-downloader tried this approach and it now fails. | Continue relying on user-exported Netscape cookies. |
| Downloading wishlisted / followed items | Users want "everything I've saved," not just purchases. | Wishlist and followed-artist pages use different API endpoints; these items are not purchased and lack download rights. Significant scope expansion with unclear value. | Out of scope per PROJECT.md. Document this limitation explicitly. |
| Metadata tagging (ID3/Vorbis comments) | Users want genre, year, cover art embedded. Requested in Ezwen issue tracker. | yt-dlp already handles metadata embedding via `--embed-thumbnail`, `--add-metadata`. Reimplementing this in bcdl duplicates complex logic. | Expose `--yt-dlp-args` so users who want tagging can pass yt-dlp flags directly. Document common recipes in README. |

## Feature Dependencies

```
[Resume / skip-downloaded]
    └──requires──> [State file (persisted download log)]
                       └──required by──> [Incremental sync]

[Incremental sync]
    └──requires──> [State file (persisted download log)]
    └──enhances──> [Resume / skip-downloaded]

[Format selection]
    └──requires──> [yt-dlp passthrough working]

[yt-dlp passthrough args]
    └──enhances──> [Format selection]
    └──enables──> [Metadata tagging (user-driven)]

[Date-range filtering]
    └──requires──> [Pagination order guarantee (newest-first)]

[Dry-run mode]
    └──enhances──> [Filter by artist/album]
    └──enhances──> [Incremental sync]

[Structured failure log]
    └──requires──> [Per-item error capture]
    └──requires──> [Retry logic]
```

### Dependency Notes

- **Resume requires state file:** The state file (keyed by item URL or tralbum_id) is the shared foundation for both resume-after-interrupt and incremental-sync. Build this once and both features use it.
- **Incremental sync requires pagination order:** The optimization of stopping pagination early only works if Bandcamp returns items newest-first. Verify this assumption before relying on it; fall back to full-fetch + state-file deduplication if order is not guaranteed.
- **Dry-run enhances filters:** Users most commonly use dry-run together with `--filter` or `--since` to preview what a targeted run would fetch. These are independent features but frequently combined.
- **yt-dlp passthrough enables metadata tagging:** Rather than building tagging logic into bcdl, `--yt-dlp-args` delegates this to yt-dlp's mature implementation and avoids reimplementing it.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed for a production-hardened public release.

- [ ] Resume / skip already-downloaded — without this, any interruption forces a full restart; a deal-breaker for large collections
- [ ] Retry on transient failures — required for reliability; API rate limits are real and frequent
- [ ] Format selection (`--format`) — users who want FLAC cannot use a tool that doesn't expose this
- [ ] Suppressed yt-dlp output with clear per-item status — current stdout flood is the most visible UX problem
- [ ] Final summary with failed item list — users need actionable output when something goes wrong
- [ ] Configurable output directory (`--output`) — currently hardcoded to cwd; expected by all users
- [ ] Helpful error on missing yt-dlp — prevents confusing crash for new users

### Add After Validation (v1.x)

Features to add once core is working.

- [ ] Incremental sync — trigger: users report running bcdl on a schedule and waiting for full-collection re-check
- [ ] Filter by artist / album name (`--filter`) — trigger: users with large collections ask for targeted downloads
- [ ] Dry-run mode (`--dry-run`) — trigger: users want to preview before running; low effort add after core is stable
- [ ] Date-range filtering (`--since DATE`) — trigger: complements incremental sync for date-based workflows
- [ ] Structured failure log (`--failed-log FILE`) — trigger: users report needing retry scripts after large batch failures

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] yt-dlp passthrough args (`--yt-dlp-args`) — defer: useful for power users but adds surface area; introduce after core flags are stable and well-documented
- [ ] Environment variable configuration — defer: bandsnatch supports `BS_` prefix env vars; valuable for CI/automation use cases but adds documentation burden

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Resume / skip-downloaded | HIGH | MEDIUM | P1 |
| Retry on transient failures | HIGH | LOW | P1 |
| Format selection | HIGH | LOW | P1 |
| Suppressed yt-dlp output + per-item status | HIGH | LOW | P1 |
| Final summary with fail list | MEDIUM | LOW | P1 |
| Configurable output directory | HIGH | LOW | P1 |
| Helpful error on missing yt-dlp | MEDIUM | LOW | P1 |
| Incremental sync | HIGH | MEDIUM | P2 |
| Filter by artist/album | MEDIUM | LOW | P2 |
| Dry-run mode | MEDIUM | LOW | P2 |
| Date-range filtering | MEDIUM | LOW | P2 |
| Structured failure log | MEDIUM | LOW | P2 |
| yt-dlp passthrough args | LOW | LOW | P3 |
| Environment variable config | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch
- P2: Should have, add when possible
- P3: Nice to have, future consideration

## Competitor Feature Analysis

| Feature | Ezwen/bandcamp-collection-downloader (Kotlin) | easlice/bandcamp-downloader (Python) | bandsnatch (Rust) | bcdl (current) |
|---------|----------------------------------------------|--------------------------------------|-------------------|----------------|
| Resume via cache file | Yes (.cache file) | Yes (file size check) | Yes (.cache file) | No |
| Format selection | Yes (8 formats) | Yes (8 formats, default mp3-320) | Yes (8 formats) | No |
| Parallel downloads | Yes (4 threads default) | Yes (5 threads default) | Yes (4 threads default) | No (sequential) |
| Retry logic | Yes (`--retries`, default 3) | Yes (`--max-download-attempts`, default 5) | No explicit flag | No |
| Output directory flag | Yes (`--download-folder`) | Yes (`--directory`) | Yes (`--output-folder`) | No (cwd only) |
| Dry-run mode | Yes (`--dry-run`) | Yes (`--dry-run`) | Yes (`--dry-run`) | No |
| Date-based filtering | No | Yes (`--download-since`, `--download-until`) | No | No |
| Artist/album filtering | No | No | No | No |
| Custom filename format | No | Yes (`--filename-format`) | No | No |
| Browser cookie auto-detect | No (file only) | Yes (6 browsers) | No (file only) | No (file only) |
| Verbose/debug logging | No | Yes (`--verbose`) | Yes (`--debug`) | No |
| Hidden item skip | Yes (`--skip-hidden`) | Yes (default behavior) | No | No |

## Sources

- Ezwen/bandcamp-collection-downloader README: https://github.com/Ezwen/bandcamp-collection-downloader (MEDIUM confidence — WebFetch)
- easlice/bandcamp-downloader README: https://github.com/easlice/bandcamp-downloader (MEDIUM confidence — WebFetch)
- bandsnatch README: https://github.com/Ovyerus/bandsnatch (MEDIUM confidence — WebFetch)
- Metalnem/bandcamp-downloader README: https://github.com/Metalnem/bandcamp-downloader (MEDIUM confidence — WebFetch)
- Ezwen/bandcamp-collection-downloader issues: https://github.com/Ezwen/bandcamp-collection-downloader/issues (MEDIUM confidence — WebFetch)
- easlice/bandcamp-downloader issues: https://github.com/easlice/bandcamp-downloader/issues (MEDIUM confidence — WebFetch)
- bandsnatch issues: https://github.com/Ovyerus/bandsnatch/issues (MEDIUM confidence — WebFetch)
- GitHub topic page bandcamp-downloader: https://github.com/topics/bandcamp-downloader (MEDIUM confidence — WebFetch)
- bcdl.py current implementation: /Users/jolilius/home/src/bcdl/bcdl.py (HIGH confidence — direct read)
- .planning/PROJECT.md and CONCERNS.md (HIGH confidence — direct read)

---
*Feature research for: Bandcamp purchased collection CLI downloader*
*Researched: 2026-03-19*
