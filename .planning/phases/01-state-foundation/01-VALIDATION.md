---
phase: 1
slug: state-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (already in dev deps) |
| **Config file** | none — discovered via conftest.py |
| **Quick run command** | `uv run pytest tests/test_bcdl.py -x -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~1 second |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x -q`
- **After every plan wave:** Run `uv run pytest -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~1 second

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 0 | RESM-01/SC-1 | unit | `uv run pytest tests/test_bcdl.py -k "test_ytdlp_not_installed" -x` | ❌ W0 | ⬜ pending |
| 1-01-02 | 01 | 0 | RESM-01/SC-2 | unit | `uv run pytest tests/test_bcdl.py -k "test_state_written_after_download" -x` | ❌ W0 | ⬜ pending |
| 1-01-03 | 01 | 0 | RESM-01/SC-3 | unit | `uv run pytest tests/test_bcdl.py -k "test_atomic_write" -x` | ❌ W0 | ⬜ pending |
| 1-01-04 | 01 | 0 | RESM-01/SC-4 | unit | `uv run pytest tests/test_bcdl.py -k "test_skip_already_downloaded" -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bcdl.py` — add stubs/tests for RESM-01 (yt-dlp detection, state file write, atomic write, skip logic)
- [ ] Update `ITEM_A` / `ITEM_B` fixtures (or add new fixtures) to include `sale_item_id` field

*Existing pytest + conftest.py infrastructure covers all other test requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `sale_item_id` field present in live Bandcamp API responses | RESM-01/SC-2 | Live API required; cannot mock without confirmed field name | Run `bcdl testuser` with a real cookies file, inspect `.bcdl/testuser.json` for numeric keys |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 2s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
