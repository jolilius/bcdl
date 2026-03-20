---
phase: 03
slug: feature-completion-and-release
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-20
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | pyproject.toml (pytest via `uv run pytest`) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -q` |
| **Estimated runtime** | ~12 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~12 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 (RED) | 01 | 1 | DCTL-01 | unit | `python -m pytest tests/test_bcdl.py -k "TestFormatFlag" -x -q` | ❌ W0 | ⬜ pending |
| 03-01-02 (GREEN) | 01 | 1 | DCTL-01 | unit | `python -m pytest tests/test_bcdl.py -x -q` | ✅ | ⬜ pending |
| 03-02-01 | 02 | 2 | DOCS-01 | manual | README review | ✅ | ⬜ pending |
| 03-03-01 | 03 | 3 | — | manual | `uv build --wheel && pipx install dist/bcdl-*.whl && bcdl --help` | ✅ | ⬜ pending |
| 03-03-02 | 03 | 3 | — | syntax | `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bcdl.py` — add `TestFormatFlag` stub class with failing tests for `--format` flag
- [ ] `.github/workflows/` — directory must exist before CI YAML can be written

*Existing test infrastructure (59 tests, pytest config in pyproject.toml) covers all other phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| README is followable by non-developer | DOCS-01 | Readability cannot be automated | Read README cold; can a non-technical Bandcamp user install and run bcdl with no other context? |
| `pipx install dist/bcdl-*.whl` + `bcdl --help` works | DIST-01 | Requires pipx installed and real wheel build | Run `uv build --wheel` then `pipx install dist/bcdl-0.1.0-py3-none-any.whl`; verify `bcdl --help` shows all flags |
| `--format flac` passes correct flags to yt-dlp | DCTL-01 | yt-dlp not installed in test env | Inspect cmd list in test mock; verify `["-x", "--audio-format", "flac"]` is appended |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
