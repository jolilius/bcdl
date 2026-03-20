---
phase: 02-download-reliability
plan: 01
subsystem: download
tags: [subprocess, yt-dlp, error-classification, tdd, pytest]

# Dependency graph
requires:
  - phase: 01-state-foundation
    provides: bcdl.py with download_item and subprocess.run usage
provides:
  - classify_yt_dlp_error(stderr) returning transient/permanent/unknown
  - _run_yt_dlp(cmd) returning (returncode, stderr) with stdout=DEVNULL, stderr=PIPE
  - _extract_error_summary(stderr) returning first ERROR: line truncated to 80 chars
  - TRANSIENT_PATTERNS and PERMANENT_PATTERNS module-level constants
affects: [02-02-download-with-retry]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Classify yt-dlp errors by stderr string matching — permanent patterns checked first"
    - "subprocess.run with stdout=DEVNULL, stderr=PIPE for clean output capture"
    - "TDD: RED tests first, then GREEN implementation, no refactor needed"

key-files:
  created: []
  modified:
    - bcdl.py
    - tests/test_bcdl.py

key-decisions:
  - "TRANSIENT_PATTERNS checked after PERMANENT_PATTERNS so mixed-signal stderr (403 + 429) returns permanent"
  - "HTTP Error 5 prefix covers 500/502/503/504 with a single pattern entry"
  - "Existing TestDownloadItem mocks updated with proc.stderr = '' to prevent TypeError after refactor"

patterns-established:
  - "Pattern: error classification helpers placed after HEADERS constant, before load_state"
  - "Pattern: _run_yt_dlp as thin subprocess wrapper, testable in isolation"

requirements-completed: [RELY-01]

# Metrics
duration: 2min
completed: 2026-03-20
---

# Phase 02 Plan 01: Error Classification Helpers Summary

**classify_yt_dlp_error, _run_yt_dlp, and _extract_error_summary added to bcdl.py with full TDD coverage — foundation for retry wrapper in Plan 02**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-20T10:57:46Z
- **Completed:** 2026-03-20T10:59:30Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added TRANSIENT_PATTERNS (5 patterns) and PERMANENT_PATTERNS (4 patterns) as module-level constants
- Implemented classify_yt_dlp_error with permanent-first checking to handle mixed-signal stderr
- Implemented _run_yt_dlp with stdout=DEVNULL, stderr=PIPE — clean output foundation for Plan 02
- Implemented _extract_error_summary extracting first ERROR: line, truncated to 80 chars
- Updated all 4 existing TestDownloadItem subprocess mocks with proc.stderr = "" (Pitfall 6 prevention)
- Added 20 new tests across TestClassifyYtdlpError (13), TestExtractErrorSummary (4), TestRunYtDlp (3)
- Test count: 26 existing → 46 total, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix existing test mocks and add error classification with TDD** - `3d4d13e` (feat)

**Plan metadata:** (docs commit follows)

_Note: TDD task — RED tests written first, then GREEN implementation in single commit_

## Files Created/Modified
- `bcdl.py` - Added TRANSIENT_PATTERNS, PERMANENT_PATTERNS, classify_yt_dlp_error, _run_yt_dlp, _extract_error_summary (48 lines added)
- `tests/test_bcdl.py` - Added TestClassifyYtdlpError, TestExtractErrorSummary, TestRunYtDlp classes + updated 4 existing mocks (97 lines added)

## Decisions Made
- Permanent patterns checked before transient so "HTTP Error 403\nHTTP Error 429" returns "permanent" — a 403 is authoritative even if 429 also present
- Used "HTTP Error 5" prefix pattern (not "HTTP Error 50") to cover all 5xx codes (500/502/503/504) with one entry
- No refactor step needed — implementation was clean on first pass

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- classify_yt_dlp_error, _run_yt_dlp, _extract_error_summary all ready for use in Plan 02 download_with_retry
- All 46 tests green — no regressions
- download_item still uses subprocess.run directly; Plan 02 will replace that call with _run_yt_dlp + retry wrapper

---
*Phase: 02-download-reliability*
*Completed: 2026-03-20*
