# Roadmap: bcdl — Bandcamp Collection Downloader

## Overview

bcdl is a functional but not production-hardened CLI tool. The roadmap hardens it into a credible v1: first by adding state tracking (the irreversible foundation everything else depends on), then by making downloads reliably self-correcting (retry + clean output as one coupled unit), then by completing the feature set (format selection, resume, README) and verifying the package distributes correctly.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: State Foundation** - Add StateManager and harden existing error paths before any new features (completed 2026-03-19)
- [ ] **Phase 2: Download Reliability** - Retry logic and yt-dlp output capture ship together as one coupled unit
- [ ] **Phase 3: Feature Completion and Release** - Format selection, resume wiring, README, and packaging verification

## Phase Details

### Phase 1: State Foundation
**Goal**: Users get actionable errors and a correctly-keyed state file that will not need to be invalidated when future phases build on it
**Depends on**: Nothing (first phase)
**Requirements**: RESM-01
**Success Criteria** (what must be TRUE):
  1. Running `bcdl` when yt-dlp is not installed shows a clear install message, not a Python traceback
  2. A `.bcdl/{username}.json` state file is created after a successful download run and contains the downloaded items keyed by stable numeric ID
  3. State file writes survive Ctrl-C without corruption — a partial run leaves the file readable, not truncated
  4. Running `bcdl` a second time skips items already in the state file and prints a skip message per item
**Plans:** 1/1 plans complete
Plans:
- [ ] 01-01-PLAN.md — TDD: state functions (load/save), yt-dlp detection, state-aware download loop

### Phase 2: Download Reliability
**Goal**: Downloads survive transient Bandcamp failures without user intervention, and yt-dlp output is replaced by clean per-item status lines
**Depends on**: Phase 1
**Requirements**: RELY-01
**Success Criteria** (what must be TRUE):
  1. A simulated HTTP 429 or 5xx during download is retried automatically with backoff; the terminal shows a retry notice, not a crash
  2. A 404 or auth failure (401/403) is not retried — it fails immediately with a clear error
  3. The terminal shows one status line per item (artist — title: OK / FAILED) instead of raw yt-dlp output
  4. A final summary shows total downloaded, skipped, and failed counts after every run
**Plans:** 1/2 plans executed
Plans:
- [ ] 02-01-PLAN.md — Error classification helpers, subprocess capture, and test foundation (TDD)
- [ ] 02-02-PLAN.md — Retry wrapper, main() refactor, clean output, and final summary

### Phase 3: Feature Completion and Release
**Goal**: Users can select audio format and direct output location, the tool is documented for non-developer users, and the PyPI package installs and runs correctly
**Depends on**: Phase 2
**Requirements**: DCTL-01, DOCS-01
**Success Criteria** (what must be TRUE):
  1. `bcdl --format flac username` downloads in FLAC where available; `--format mp3` downloads in MP3
  2. `pipx install bcdl` installs the tool and `bcdl --help` works from a clean environment
  3. The README documents every flag with a concrete usage example, and a non-developer Bandcamp user can follow it to completion without needing to read the source
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. State Foundation | 1/1 | Complete    | 2026-03-19 |
| 2. Download Reliability | 1/2 | In Progress|  |
| 3. Feature Completion and Release | 0/? | Not started | - |
