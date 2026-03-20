---
phase: 2
slug: download-reliability
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | none — pytest auto-discovers tests/ |
| **Quick run command** | `python -m pytest tests/test_bcdl.py -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_bcdl.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green (26+ tests passing)
- **Max feedback latency:** ~3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | RELY-01 | unit | `python -m pytest tests/test_bcdl.py -x -q` | ✅ | ⬜ pending |
| 2-01-02 | 01 | 1 | RELY-01 | unit | `python -m pytest tests/test_bcdl.py::TestClassifyYtdlpError -x -q` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | RELY-01 | unit | `python -m pytest tests/test_bcdl.py::TestRetryLogic -x -q` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 2 | RELY-01 | unit | `python -m pytest tests/test_bcdl.py::TestDownloadOutput -x -q` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 2 | RELY-01 | unit | `python -m pytest tests/test_bcdl.py::TestMainSummary -x -q` | ❌ W0 | ⬜ pending |
| 2-01-06 | 01 | 3 | RELY-01 | unit | `python -m pytest tests/ -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bcdl.py` — update all existing `subprocess.run` mocks to add `mock_result.stderr = ""` (prevents TypeError after refactor)
- [ ] `tests/test_bcdl.py` — add `TestClassifyYtdlpError` class with tests for each pattern category (transient, permanent, unknown)
- [ ] `tests/test_bcdl.py` — add `TestRetryLogic` class: transient retries with backoff, permanent fails immediately, max retries exhausted
- [ ] `tests/test_bcdl.py` — add `TestDownloadOutput` class: stdout=DEVNULL verified, single status line per item (not raw yt-dlp output)
- [ ] `tests/test_bcdl.py` — add `TestMainSummary` class: final summary shows downloaded/skipped/failed counts

*No new test files needed — all additions to existing `tests/test_bcdl.py`.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| yt-dlp --quiet actually suppresses Bandcamp progress output | RELY-01 | Requires live Bandcamp URL + real yt-dlp invocation | Run `bcdl <username> --cookies <file>` on ≥1 item; confirm terminal shows `[1/N] Artist — Title: OK` only, no yt-dlp progress bars |
| HTTP 429 triggers retry notice in terminal | RELY-01 | Requires simulated or live rate-limit response | Mock verified in unit tests; live validation optional during Phase 2 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
