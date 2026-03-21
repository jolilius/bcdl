# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.0 — MVP

**Shipped:** 2026-03-21
**Phases:** 3 | **Plans:** 6 | **Timeline:** 4 days (2026-03-17 → 2026-03-21)

### What Was Built

- Atomic JSON state tracking keyed by `sale_item_id` — skip-on-rerun, Ctrl-C safe, no state corruption
- Error classification (TRANSIENT/PERMANENT) with exponential backoff retry; clean per-item status output replacing raw yt-dlp noise
- `--format` flag with pre-network validation, threaded end-to-end to yt-dlp subprocess
- Non-developer README with pipx-first install + cookies walkthrough; GitHub Actions CI; installable wheel

### What Worked

- **TDD throughout:** Every plan was RED → GREEN. Tests caught mock contract bugs (e.g., `_backoff_delay` needing `return_value=float`) before they became silent failures.
- **Coupling Phase 2 as one unit:** Shipping error classification, subprocess capture, retry logic, and clean output together in one phase prevented a common failure mode where capturing output ships without retry or vice versa.
- **Format validation before network call:** The decision to validate `--format` after yt-dlp check but before `requests.get` means invalid format exits immediately with no I/O cost — caught by tests cleanly.
- **Atomic write pattern established early:** `NamedTemporaryFile(dir=path.parent) + os.replace` in Phase 1 meant Phase 2 and 3 inherited Ctrl-C safety for free.

### What Was Inefficient

- **`download_item` not removed:** Phase 2 introduced `download_with_retry` to replace `download_item`, but `download_item` was retained "for backward compatibility." It became dead code with live tests, which is worse than deletion. Should have been removed in the same PR.
- **VALIDATION.md files left in draft:** All three Nyquist validation files were created as planning artifacts but never updated post-execution. They add noise to future audits.
- **PROJECT.md fell behind:** PROJECT.md was only updated after Phase 1; Phases 2 and 3 decisions accumulated in STATE.md without flowing back. Required a catch-up review at milestone completion.

### Patterns Established

- **Atomic write pattern:** `NamedTemporaryFile(mode='w', dir=path.parent, delete=False, suffix='.tmp') + os.replace` — use for any state file write
- **Per-item state write (not post-loop):** `save_state` called inside the loop after each success, not after the entire loop, for Ctrl-C safety
- **PERMANENT before TRANSIENT in error classification:** Mixed stderr (e.g., both 403 and 429 in one output) resolves as permanent — fail fast is safer
- **`audio_format` parameter naming:** Avoid shadowing Python builtins; `audio_format` not `format`
- **`return_value=float` in backoff mocks:** Any function that formats its return value (`:.0f`) must have `return_value=concrete_type` in patches, not bare `patch()`

### Key Lessons

1. **Remove dead code in the same commit it's superseded.** `download_item` should have been deleted the moment `download_with_retry` replaced it in `main()`. Dead code with passing tests is worse than no tests — it provides false safety signals.
2. **Update project docs at each phase, not just at milestones.** PROJECT.md diverged from reality after Phase 1. A 30-second update after each phase prevents a large catch-up review at milestone close.
3. **Packaging smoke tests need human checkpoints explicitly.** The `bcdl --help` smoke test after pipx install correctly required a human checkpoint — this should be the default for any distribution verification step.

### Cost Observations

- Model mix: ~100% sonnet (balanced profile throughout)
- Sessions: ~4-5 sessions across 4 days
- Notable: TDD discipline kept context windows lean — tests defined the interface before implementation, reducing back-and-forth clarification cycles

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Phases | Plans | Key Change |
|-----------|--------|-------|------------|
| v1.0 | 3 | 6 | First milestone; TDD + GSD workflow established |

### Cumulative Quality

| Milestone | Tests | Zero-Dep Additions |
|-----------|-------|--------------------|
| v1.0 | 65 | stdlib only (os, shutil, tempfile, datetime, random) |

### Top Lessons (Verified Across Milestones)

1. Delete superseded code in the same commit — dead code with tests is a liability
2. Keep PROJECT.md current at each phase boundary, not just milestones
