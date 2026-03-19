---
phase: 01-state-foundation
plan: 01
subsystem: cli
tags: [python, json, stdlib, state-tracking, atomic-write, yt-dlp]

# Dependency graph
requires: []
provides:
  - load_state(path) function in bcdl.py: resilient JSON state loader returning {} on missing/corrupt
  - save_state(state, path) function in bcdl.py: atomic JSON write via NamedTemporaryFile + os.replace
  - yt-dlp detection in main() using shutil.which before any network calls
  - state-aware download loop: skip already-downloaded items, record successful downloads
  - .bcdl/{username}.json state file keyed by str(sale_item_id)
affects: [02-progress-display, 03-packaging]

# Tech tracking
tech-stack:
  added: [os (stdlib), shutil (stdlib), tempfile (stdlib), datetime+timezone (stdlib), pathlib.Path (stdlib)]
  patterns:
    - atomic-file-write: NamedTemporaryFile(dir=path.parent, delete=False) + os.replace
    - resilient-load: return {} on FileNotFoundError, {} + stderr warning on JSONDecodeError
    - fail-fast-detection: shutil.which before first network call
    - per-item-state-write: save_state inside loop after each success, not after loop end

key-files:
  created: []
  modified:
    - bcdl.py
    - tests/test_bcdl.py

key-decisions:
  - "State keyed by str(sale_item_id) — items missing this field download every time, never get a state entry"
  - "save_state called inside download loop after each success, not at end of loop (Ctrl-C safety)"
  - "NamedTemporaryFile dir=path.parent mandatory — avoids cross-filesystem os.replace failure"
  - "load_state returns {} silently on missing file, but prints Warning to stderr on corrupt JSON"
  - "Skip output format: [skip] Artist \u2014 Title (em dash, not hyphen)"

patterns-established:
  - "Atomic write pattern: NamedTemporaryFile(mode='w', dir=path.parent, delete=False, suffix='.tmp') + os.replace"
  - "Resilient load pattern: try/except FileNotFoundError silently, JSONDecodeError with warning"
  - "Fail-fast CLI check: shutil.which before any I/O, sys.exit(1) with exact error message"

requirements-completed: [RESM-01]

# Metrics
duration: 2min
completed: 2026-03-19
---

# Phase 1 Plan 1: State Foundation Summary

**JSON state tracking with atomic writes in bcdl.py: load_state/save_state functions, yt-dlp fail-fast detection, and skip-on-rerun download loop keyed by sale_item_id**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-19T12:30:23Z
- **Completed:** 2026-03-19T12:32:26Z
- **Tasks:** 2 (TDD: RED + GREEN)
- **Files modified:** 2

## Accomplishments

- Implemented `load_state(path)` and `save_state(state, path)` using only Python stdlib
- Added `shutil.which("yt-dlp")` check at startup before any network calls, with exact error message
- Replaced bare download loop with state-aware loop: skips items in `.bcdl/{username}.json`, writes state atomically after each successful download
- All 26 tests pass (14 existing + 12 new)

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for all state behaviors** - `0399e4f` (test)
2. **Task 2: Implement state functions and yt-dlp detection, wire into main()** - `67bd213` (feat)

_Note: TDD plan — test commit (RED) followed by implementation commit (GREEN)_

## Files Created/Modified

- `/Users/jolilius/home/src/bcdl/bcdl.py` - Added load_state, save_state, yt-dlp detection, state-aware download loop
- `/Users/jolilius/home/src/bcdl/tests/test_bcdl.py` - Added 3 new fixtures and 4 test classes (TestYtdlpDetection, TestLoadState, TestSaveState, TestStateIntegration)

## Decisions Made

- Kept state management as module-level functions in `bcdl.py` (not a class, not a new module) — appropriate for a 186-line codebase
- Used `str(item.get("sale_item_id", ""))` guard so empty string is never a valid state key
- `save_state` called per-item inside the loop (not after the loop) to ensure Ctrl-C at item 50/100 saves the first 50

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- State foundation complete; Phase 2 (progress display) can rely on `load_state`/`save_state` being importable from `bcdl`
- `.bcdl/{username}.json` format is now locked — Phase 2 and 3 should treat it as stable
- No blockers

---
*Phase: 01-state-foundation*
*Completed: 2026-03-19*
