# Phase 2: Download Reliability - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Retry logic and yt-dlp output capture ship together as one coupled unit. Specifically:
1. Detect transient failures (HTTP 429, 5xx, timeouts) and retry automatically with exponential backoff
2. Detect permanent failures (HTTP 404, 401, 403) and fail immediately — no retry
3. Suppress raw yt-dlp terminal output; replace with clean per-item status lines
4. Show a final summary with downloaded / skipped / failed counts

Format selection, output directory, and CLI retry flags are explicitly out of scope (Phase 3 and v2).

</domain>

<decisions>
## Implementation Decisions

### Status line format
- Single line per item: print `[  1/42] Artist — Title: ` (with trailing space) before the subprocess call, then append `OK` or `FAILED (reason)` on the same line when done
- Index is zero-padded to align with total width: `[  1/42]`, `[ 10/42]`, `[42/42]`
- No URL shown — raw yt-dlp URL output is suppressed along with everything else
- `[skip] Artist — Title` format from Phase 1 stays unchanged — visually distinct from download lines

### Retry verbosity
- When a transient error triggers a retry, print an indented notice on a new line: `  [retry 1/3] waiting 10s…`
- Show the wait duration so the user knows the tool isn't frozen
- After all retries exhausted, print `FAILED (retried 3x: <reason>)` on the original item line

### Final summary
- Show all three counts: `Done: 38 downloaded, 3 skipped, 1 failed.`
- `skipped` counter must be added to the download loop (currently there is none)
- When items failed, list them with failure reason: `  - Burial — Untrue (HTTP Error 404)` or `  - Artist — Title (retried 3x: HTTP Error 429)`

### Retry parameters
- Hardcoded for Phase 2: max_retries=3, base_delay=5s, cap=60s, ±25% jitter
- RELY-04 (configurable retry flags) stays in v2 scope — no `--max-retries` or `--retry-delay` flags in this phase

### Claude's Discretion
- Exact zero-padding width calculation (use `len(str(total))` for dynamic width)
- Whether retry notice overwrites or appends to existing terminal line (appending to new line is fine)
- `_extract_error_summary` truncation length (80 chars is fine)
- Whether `classify_yt_dlp_error` and `download_with_retry` live as top-level functions or are reorganized

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — RELY-01 (v1, this phase), RELY-02 (v2 but coupled here per roadmap); RELY-04 is v2 and explicitly NOT in scope

### Roadmap
- `.planning/ROADMAP.md` — Phase 2 success criteria (4 items) define exactly what must be TRUE; hardcoded retry defaults must satisfy criterion 1 and 2

### Research
- `.planning/phases/02-download-reliability/02-RESEARCH.md` — Full pattern library: subprocess DEVNULL/PIPE pattern, error string taxonomy (TRANSIENT_PATTERNS, PERMANENT_PATTERNS), backoff formula, pitfalls (esp. Pitfall 1: deadlock, Pitfall 2: --quiet flag, Pitfall 6: mock updates needed), code examples

No external specs — requirements are fully captured in decisions above and roadmap success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `download_item()` at `bcdl.py:128` — current function to be refactored into `download_with_retry()`; existing signature `(item, index, total, cookies_file)` should be preserved or extended
- `main()` at `bcdl.py:151` — download loop, `failed: list[dict]`, `time.sleep(args.delay)` inter-item delay all live here; `skipped` counter needs to be added
- `subprocess` already imported; `time` and `random` already imported (or need to be)

### Established Patterns
- Tests use `unittest.mock.patch` + `pytest` — all `subprocess.run` mocks currently return `MagicMock(returncode=0)` without `.stderr`; these MUST be updated to include `mock_result.stderr = ""` or they will `TypeError` after refactor (see RESEARCH.md Pitfall 6)
- Error handling in `main()` uses `sys.exit(1)` pattern for fatal errors — permanent download failures are NOT fatal (loop continues), only collection-fetch errors exit

### Integration Points
- `download_item()` call site in `main()` at `bcdl.py:215` — replace with `download_with_retry()` call
- Summary print at `bcdl.py:231` — replace with three-count summary
- `failed.append(item)` at `bcdl.py:217` — needs to also store failure reason for end-of-run display

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- `--max-retries` and `--retry-delay` CLI flags — RELY-04, explicitly v2 scope
- Retry-After header parsing from Bandcamp 429 responses — future phase if needed

</deferred>

---

*Phase: 02-download-reliability*
*Context gathered: 2026-03-20*
