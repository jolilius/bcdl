---
phase: 02-download-reliability
plan: 02
subsystem: download
tags: [retry, backoff, subprocess, yt-dlp, status-output, summary]

# Dependency graph
requires:
  - phase: 02-download-reliability-01
    provides: classify_yt_dlp_error, _run_yt_dlp, _extract_error_summary, TRANSIENT_PATTERNS, PERMANENT_PATTERNS
provides:
  - download_with_retry function with transient/permanent error classification and exponential backoff
  - _backoff_delay function with configurable base, cap, and 25% jitter
  - Clean per-item status lines replacing raw yt-dlp output
  - Three-count final summary (downloaded, skipped, failed) with failed item details
  - TestRetryLogic, TestDownloadOutput, TestMainSummary test classes
affects:
  - 03-packaging
  - any phase that calls into main() or download loop

# Tech tracking
tech-stack:
  added: [random (stdlib, jitter for backoff)]
  patterns:
    - download_with_retry wraps _run_yt_dlp in a for-loop retry with classify_yt_dlp_error dispatch
    - _backoff_delay returns actual delay (float) so retry notice can print it
    - main() stores failed as list[tuple[dict, str]] to carry reason through to summary

key-files:
  created: []
  modified:
    - bcdl.py
    - tests/test_bcdl.py

key-decisions:
  - "_backoff_delay returns float (actual delay) so download_with_retry can print it in the retry notice — side effect of making it mockable to a concrete return_value"
  - "Test patches of _backoff_delay require return_value=float, not bare patch(), because the return value is formatted with :.0f in the retry notice print"
  - "download_with_retry uses width=len(str(total)) for dynamic zero-padding of index in status line"

patterns-established:
  - "Status line pattern: print prefix with end='' flush=True before subprocess, then print OK or FAILED(reason) after"
  - "Retry loop: for attempt in range(max_retries + 1) — initial attempt is attempt 0"
  - "main() failed list stores (item, reason) tuples to carry error context to summary"

requirements-completed: [RELY-01]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 2 Plan 02: Download Reliability Core Summary

**download_with_retry with exponential backoff (3x, 5-60s), clean per-item status lines suppressing raw yt-dlp output, and three-count final summary with failure reasons**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-03-20T11:00:56Z
- **Completed:** 2026-03-20T11:03:54Z
- **Tasks:** 1 of 2 complete (Task 2 is checkpoint:human-verify, awaiting user)
- **Files modified:** 2

## Accomplishments
- Implemented `_backoff_delay` with exponential backoff (base 5s, cap 60s, 25% jitter)
- Implemented `download_with_retry` that retries transient errors (429/5xx) with backoff, fails immediately on permanent (404/401/403) and unknown errors, and prints clean status lines
- Refactored `main()` to use `download_with_retry`, added `skipped` counter, changed `failed` to `list[tuple[dict, str]]`, updated final summary to three-count format with failure reasons
- Added 13 new tests across TestRetryLogic (6), TestDownloadOutput (4), TestMainSummary (3)
- Updated TestStateIntegration (4 tests) to mock `download_with_retry` instead of `download_item`

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `a72542f` (test)
2. **Task 1 GREEN: Implementation** - `8be22e2` (feat)

_Note: TDD tasks have two commits (test RED → feat GREEN)_

## Files Created/Modified
- `/Users/jolilius/home/src/bcdl/bcdl.py` - Added `_backoff_delay`, `download_with_retry`; refactored `main()` download loop and summary
- `/Users/jolilius/home/src/bcdl/tests/test_bcdl.py` - Added TestRetryLogic, TestDownloadOutput, TestMainSummary; updated TestStateIntegration mocks

## Decisions Made
- `_backoff_delay` returns the actual delay as a float (not None) so it can be printed in the retry notice. This also means test patches must specify `return_value=5.0` (not bare `patch()`) to avoid `:.0f` format string TypeError on MagicMock.
- `download_with_retry` uses `width = len(str(total))` for dynamic index padding in status lines, matching the context decision.
- `main()` no longer prints `"Waiting Ns..."` between items — the inter-item `time.sleep(args.delay)` is preserved but the decorative print is removed to keep output clean.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test mock for _backoff_delay needed explicit return_value=float**
- **Found during:** Task 1 GREEN (running tests after implementation)
- **Issue:** `patch("bcdl._backoff_delay")` without `return_value` returns a MagicMock; when `download_with_retry` uses `f"{actual_delay:.0f}s"`, Python raises `TypeError: unsupported format string passed to MagicMock.__format__`
- **Fix:** Changed two test patches from bare `patch("bcdl._backoff_delay")` to `patch("bcdl._backoff_delay", return_value=5.0)`
- **Files modified:** tests/test_bcdl.py
- **Verification:** All 59 tests pass
- **Committed in:** `8be22e2` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 - bug in test fixture)
**Impact on plan:** Necessary fix — tests would otherwise TypeError on transient retry paths. No scope creep.

## Issues Encountered
None beyond the mock return value issue documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Task 2 (checkpoint:human-verify) is next — user verifies terminal output format
- Phase 3 (packaging) can proceed after human approval of terminal output
- All 4 Phase 2 roadmap success criteria are satisfied by the implementation

---
*Phase: 02-download-reliability*
*Completed: 2026-03-20*
