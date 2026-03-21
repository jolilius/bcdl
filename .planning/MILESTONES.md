# Milestones

## v1.0 MVP (Shipped: 2026-03-21)

**Phases completed:** 3 phases, 6 plans
**Timeline:** 2026-03-17 → 2026-03-21 (4 days)
**Codebase:** 370 LOC (bcdl.py) + 694 LOC (tests), 65 tests passing
**Git commits:** 45

**Key accomplishments:**

1. Atomic JSON state tracking keyed by `sale_item_id` — skip-on-rerun, Ctrl-C safe atomic writes via `NamedTemporaryFile + os.replace`
2. Error classification with TRANSIENT/PERMANENT patterns — HTTP 429/5xx retry with exponential backoff (3×, 5–60s), immediate fail on 404/401/403
3. yt-dlp subprocess capture — stdout suppressed (DEVNULL), stderr piped; clean per-item status lines replace raw yt-dlp output
4. Three-count final summary (downloaded / skipped / failed) with failure reasons per item
5. `--format` flag (flac/mp3/wav/aac/opus) with pre-network validation, threaded to yt-dlp `-x --audio-format`
6. Non-developer README with pipx-first install, step-by-step cookies walkthrough, all 4 flags documented; GitHub Actions CI; installable wheel (`dist/bcdl-0.1.0-py3-none-any.whl`)

**Tech debt carried forward:**

- `download_item` (bcdl.py:238-258) is dead code — unreachable in production but still tested by `TestDownloadItem`
- All `*-VALIDATION.md` files remain in `draft` state (Nyquist records not updated post-execution)

---
