---
phase: 03-feature-completion-and-release
plan: "02"
subsystem: docs
tags: [readme, ci, github-actions, pipx, yt-dlp, uv]

# Dependency graph
requires:
  - phase: 03-feature-completion-and-release
    provides: phase context with locked README structure and CI decisions
provides:
  - README.md rewritten for non-developer Bandcamp users with pipx-first install
  - .github/workflows/ci.yml that runs pytest via uv on push and PR to main
  - Documented all 4 CLI flags (--cookies, --format, --delay, --export-csv) with examples
  - Step-by-step cookies workflow naming the Get cookies.txt LOCALLY Chrome extension
affects: [03-03-packaging, users-installing-bcdl]

# Tech tracking
tech-stack:
  added: [github-actions, astral-sh/setup-uv@v7]
  patterns: [pipx as primary user install path, uv for CI dependency management]

key-files:
  created: [.github/workflows/ci.yml]
  modified: [README.md]

key-decisions:
  - "pipx install is primary install path; uv/git-clone moved to Development section for contributors only"
  - "CI uses astral-sh/setup-uv@v7 with enable-cache; Python 3.12 only via pyproject.toml requires-python (no matrix)"
  - "Get cookies.txt LOCALLY extension named explicitly with direct Chrome Web Store link"

patterns-established:
  - "README audience: non-developer Bandcamp buyers, not contributors"
  - "CI pattern: uv sync + uv run pytest, no manual python version pin"

requirements-completed: [DOCS-01]

# Metrics
duration: 8min
completed: 2026-03-21
---

# Phase 03 Plan 02: README Rewrite and GitHub Actions CI Summary

**User-facing README rewritten for non-developer Bandcamp buyers (pipx-first, cookies walkthrough, all 4 flags documented) and pytest CI added via GitHub Actions with uv**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-03-21T08:15:00Z
- **Completed:** 2026-03-21T08:23:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- Rewrote README.md from developer-focused (uv/virtualenv) to user-focused (pipx install, plain-English explanations)
- Added step-by-step cookies export walkthrough naming the specific Chrome extension and linking to the Chrome Web Store
- Documented all 4 CLI flags (--cookies, --format, --delay, --export-csv) in an options table with concrete usage examples
- Explained resume behavior (.bcdl/{username}.json), retry behavior, and summary output in a "How it works" section
- Created .github/workflows/ci.yml that triggers on push/PR to main, installs deps via uv sync, runs uv run pytest

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite README.md for non-developer users** - `0c4c71f` (docs)
2. **Task 2: Add GitHub Actions CI workflow** - `3494e39` (chore)

## Files Created/Modified

- `README.md` - Full rewrite: pipx install, prerequisites (Python, pipx, yt-dlp, ffmpeg), quick start, cookies walkthrough, options table, how-it-works section, development section
- `.github/workflows/ci.yml` - GitHub Actions CI: checkout, setup-uv with cache, uv sync, uv run pytest; triggers on push/PR to main

## Decisions Made

- pipx is primary install path with "from source" as fallback; uv workflow moved to Development section — matches CONTEXT.md locked decision
- CI uses `astral-sh/setup-uv@v7` with `enable-cache: true`; no Python version matrix since pyproject.toml pins `>=3.12`
- `--format` documented in README even though Plan 01 (which adds the flag) had not yet been executed — per plan instructions, README documents the intended final state

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- `python -c "import yaml; ..."` failed because PyYAML not installed globally; verified YAML validity using `uv run --with pyyaml python -c "..."` instead. YAML is valid.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- CI will run tests automatically once `.github/workflows/ci.yml` is pushed to GitHub
- Plan 03 (packaging verification) can proceed immediately
- Plan 01 (--format flag) can also proceed; README already documents the flag

## Self-Check: PASSED

- FOUND: README.md
- FOUND: .github/workflows/ci.yml
- FOUND: 03-02-SUMMARY.md
- FOUND commit: 0c4c71f (docs: README rewrite)
- FOUND commit: 3494e39 (chore: CI workflow)

---
*Phase: 03-feature-completion-and-release*
*Completed: 2026-03-21*
