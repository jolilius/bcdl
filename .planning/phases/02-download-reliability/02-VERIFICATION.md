---
phase: 02-download-reliability
verified: 2026-03-20T12:00:00Z
status: passed
score: 13/13 must-haves verified
re_verification: false
---

# Phase 02: Download Reliability Verification Report

**Phase Goal:** Reliable download execution with retry logic, error classification, and clean user-facing output
**Verified:** 2026-03-20T12:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

#### Plan 01 Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | classify_yt_dlp_error returns 'transient' for HTTP 429, 5xx, connection reset, timeout | VERIFIED | bcdl.py:52-61; confirmed via live import: 429->transient, 503->transient, "Connection reset"->transient, "timed out"->transient |
| 2  | classify_yt_dlp_error returns 'permanent' for HTTP 404, 401, 403, Unsupported URL | VERIFIED | bcdl.py:52-61; confirmed via live import: all four return "permanent" |
| 3  | classify_yt_dlp_error returns 'unknown' for unrecognized stderr | VERIFIED | bcdl.py:61; "unknown" returned as fallback; confirmed via live import |
| 4  | Permanent patterns checked before transient patterns | VERIFIED | bcdl.py:55-60: PERMANENT_PATTERNS loop runs first; "HTTP Error 403\nHTTP Error 429" -> "permanent" confirmed |
| 5  | _run_yt_dlp suppresses stdout (DEVNULL) and captures stderr (PIPE) | VERIFIED | bcdl.py:68-69: stdout=subprocess.DEVNULL, stderr=subprocess.PIPE inside _run_yt_dlp; TestRunYtDlp.test_passes_devnull_and_pipe asserts both |
| 6  | _extract_error_summary extracts first ERROR: line from stderr, truncated to 80 chars | VERIFIED | bcdl.py:75-80; confirmed: len(result for 200-char input) == 80 |
| 7  | Existing tests still pass after mock updates | VERIFIED | All 59 tests pass; 4 TestDownloadItem mocks have proc.stderr = "" at lines 200, 210, 219, 232 |

#### Plan 02 Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 8  | A simulated HTTP 429 during download is retried automatically with backoff; terminal shows retry notice | VERIFIED | bcdl.py:222-224; TestRetryLogic.test_transient_retry_then_success (call_count==2); TestDownloadOutput.test_retry_prints_notice asserts "[retry 1/3] waiting" in stdout |
| 9  | A 404 or auth failure (401/403) is NOT retried — fails immediately with clear error | VERIFIED | bcdl.py:216-219; TestRetryLogic.test_permanent_no_retry asserts mock_run.call_count==1 |
| 10 | Terminal shows one status line per item instead of raw yt-dlp output | VERIFIED | bcdl.py:200 uses --quiet --no-progress in cmd; _run_yt_dlp uses DEVNULL for stdout; TestDownloadOutput.test_no_raw_ytdlp_output asserts stdout=subprocess.DEVNULL |
| 11 | Final summary shows downloaded, skipped, and failed counts | VERIFIED | bcdl.py:338: `print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {len(failed)} failed.")`; TestMainSummary.test_summary_three_counts asserts exact string |
| 12 | Failed items listed with failure reason after summary | VERIFIED | bcdl.py:339-344: if failed block prints each item with reason; TestMainSummary.test_failed_items_listed asserts artist, title, and reason in output |
| 13 | Max retries exceeded marks item as failed with retry count in reason | VERIFIED | bcdl.py:225-228: returns (False, f"retried {max_retries}x: {reason}"); TestRetryLogic.test_max_retries_exhausted asserts "retried 3x" in reason and call_count==4 |

**Score:** 13/13 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `bcdl.py` | TRANSIENT_PATTERNS, PERMANENT_PATTERNS, classify_yt_dlp_error, _run_yt_dlp, _extract_error_summary | VERIFIED | All 5 symbols present at lines 37-80; substantive implementations, not stubs |
| `bcdl.py` | download_with_retry, _backoff_delay, updated main() | VERIFIED | download_with_retry at line 183 (full 48-line implementation); _backoff_delay at line 174; main() refactored at lines 310-344 |
| `tests/test_bcdl.py` | TestClassifyYtdlpError (13 tests), TestExtractErrorSummary (4 tests), TestRunYtDlp (3 tests) | VERIFIED | 13 tests in TestClassifyYtdlpError (plan specified 13; 1 bonus test_transient_500 added), 4 in TestExtractErrorSummary, 3 in TestRunYtDlp |
| `tests/test_bcdl.py` | TestRetryLogic (6 tests), TestDownloadOutput (4 tests), TestMainSummary (3 tests) | VERIFIED | Exactly 6, 4, and 3 tests respectively; all pass |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| bcdl.py:main() | bcdl.py:download_with_retry() | replaces download_item call in download loop | WIRED | Line 322: `success, reason = download_with_retry(item, i, len(items), cookies_file=args.cookies)` |
| bcdl.py:download_with_retry() | bcdl.py:_run_yt_dlp() | subprocess invocation | WIRED | Line 208: `returncode, stderr = _run_yt_dlp(cmd)` |
| bcdl.py:download_with_retry() | bcdl.py:classify_yt_dlp_error() | error classification for retry decision | WIRED | Line 214: `error_class = classify_yt_dlp_error(stderr)` |
| bcdl.py:_run_yt_dlp() | subprocess.DEVNULL, subprocess.PIPE | stdout/stderr capture | WIRED | Lines 68-69 inside _run_yt_dlp |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| RELY-01 | 02-01-PLAN.md, 02-02-PLAN.md | Tool retries failed requests automatically on transient failures (HTTP 429, 5xx, timeouts) without user intervention | SATISFIED | classify_yt_dlp_error identifies transient errors; download_with_retry loops up to max_retries=3 times with _backoff_delay; permanent/unknown errors fail immediately; all retry paths covered by TestRetryLogic |

No orphaned requirements: REQUIREMENTS.md traceability table maps RELY-01 to Phase 2 only. Both plans claim RELY-01, and the implementation satisfies it completely.

### Anti-Patterns Found

Scanned bcdl.py and tests/test_bcdl.py for stubs, placeholders, and empty implementations.

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| bcdl.py | 230 | `return False, "max retries exceeded"  # unreachable but satisfies type checker` | Info | Intentional unreachable fallback; documented in code comment; does not affect behavior |

No TODO/FIXME/placeholder comments. No empty handlers. No static API returns. No orphaned functions (`download_item` is retained for backward compatibility per plan decision and is covered by TestDownloadItem).

### Human Verification Required

#### 1. Terminal Output Visual Format

**Test:** Run `python bcdl.py username` against a real Bandcamp account, or run `python -c "import bcdl; bcdl.download_with_retry({'band_name': 'Test', 'album_title': 'Album', 'item_url': 'https://example.com'}, 1, 42)"` to observe the format with a fake URL.
**Expected:** Status line reads `[ 1/42] Test — Album: FAILED (...)` — dynamic zero-padding, em dash separator, colon before result; no raw yt-dlp progress bars visible.
**Why human:** Output formatting (padding, Unicode em dash, flush behavior) is verified by TestDownloadOutput but the visual gestalt of "clean output replacing raw yt-dlp noise" requires a human to confirm in a real terminal.

#### 2. Backoff Delay in Real Conditions

**Test:** Observe retry notice timing by triggering a real 429 response (or monkey-patching _run_yt_dlp in a REPL to return transient errors).
**Expected:** Retry notices show actual computed delay (e.g. `[retry 1/3] waiting 6s...`) and the program pauses for that duration before retrying.
**Why human:** _backoff_delay uses time.sleep(); tests mock it out. Real delay behavior cannot be verified programmatically without actually sleeping.

---

## Gaps Summary

No gaps. All 13 must-have truths are verified against the actual codebase:

- Error classification logic exists, is substantive, and is wired into the retry loop
- Subprocess capture (DEVNULL + PIPE) is present in _run_yt_dlp and verified by test assertions
- download_with_retry is fully implemented with retry loop, backoff, and clean status output
- main() uses download_with_retry (not download_item), carries failure reasons, and prints a three-count summary
- All 59 tests pass including 33 new tests covering the Phase 02 functionality
- RELY-01 is fully satisfied

Two human verification items are flagged for terminal UX confirmation, but these do not block goal achievement — the automated test coverage for output format is extensive.

---

_Verified: 2026-03-20T12:00:00Z_
_Verifier: Claude (gsd-verifier)_
