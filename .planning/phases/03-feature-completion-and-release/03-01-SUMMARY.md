---
phase: 03-feature-completion-and-release
plan: 01
subsystem: cli
tags: [argparse, yt-dlp, audio-format, tdd]

# Dependency graph
requires:
  - phase: 02-download-reliability
    provides: download_with_retry function with cookies_file parameter
provides:
  - SUPPORTED_FORMATS constant defining valid audio formats
  - --format CLI flag validated before network calls
  - audio_format parameter threaded through download_with_retry to yt-dlp cmd
affects: [03-02, 03-03, packaging]

# Tech tracking
tech-stack:
  added: []
  patterns: [validate-before-network for CLI flag validation, TDD red-green cycle]

key-files:
  created: []
  modified:
    - bcdl.py
    - tests/test_bcdl.py

key-decisions:
  - "audio_format parameter name chosen over 'format' to avoid shadowing Python built-in"
  - "Format validation occurs after yt-dlp check but before any network call (requests.get never called on invalid format)"
  - "--format with --export-csv is silently compatible: export path skips downloads entirely so no -x flag needed"

patterns-established:
  - "Validate CLI flags before any network calls — exit 1 with clear error message on invalid input"
  - "Extend yt-dlp cmd list conditionally: if audio_format: cmd += ['-x', '--audio-format', audio_format]"

requirements-completed: [DCTL-01]

# Metrics
duration: 2min
completed: 2026-03-21
---

# Phase 3 Plan 01: --format Flag Summary

**`--format` flag for yt-dlp audio extraction: SUPPORTED_FORMATS constant, argparse argument, pre-network validation, and audio_format parameter threaded through download_with_retry to yt-dlp cmd**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-21T08:15:50Z
- **Completed:** 2026-03-21T08:17:50Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments
- 6 failing tests written first (RED phase) covering flac, mp3, no-format, invalid format, validates-before-network, and csv-ignored scenarios
- SUPPORTED_FORMATS constant `("flac", "mp3", "wav", "aac", "opus")` added to bcdl.py
- `--format` argparse argument and pre-network validation added to `main()`
- `audio_format` parameter added to `download_with_retry()`, appending `-x --audio-format <fmt>` to yt-dlp cmd when set
- All 65 tests pass (59 existing + 6 new TestFormatFlag)

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing TestFormatFlag tests** - `4701c5e` (test)
2. **Task 2: GREEN — Implement --format flag in bcdl.py** - `95fb0d4` (feat)

_Note: TDD tasks have two commits (test RED, feat GREEN)_

## Files Created/Modified
- `bcdl.py` - Added SUPPORTED_FORMATS, --format argparse arg, format validation, audio_format param in download_with_retry, cmd extension, main() call threading
- `tests/test_bcdl.py` - Added TestFormatFlag class with 6 test methods

## Decisions Made
- Used `audio_format` as parameter name (not `format`) to avoid shadowing Python built-in `format()`
- Format validation placed after yt-dlp presence check but before `requests.get` — ensures no network calls on invalid format
- `--format flac` with `--export-csv` is compatible: CSV export path exits before any download call, so no `-x` flag is ever needed or passed

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `--format` flag fully implemented and tested, ready for 03-02 work
- DCTL-01 requirement satisfied

---
*Phase: 03-feature-completion-and-release*
*Completed: 2026-03-21*
