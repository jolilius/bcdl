# Phase 1: State Foundation - Context

**Gathered:** 2026-03-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Add StateManager and harden yt-dlp detection before any new features. The download loop itself is unchanged — this phase is about tracking what was downloaded and failing gracefully when yt-dlp is absent.

Specifically:
1. Detect missing yt-dlp at startup with a clear install message (not a traceback)
2. Create and maintain `.bcdl/{username}.json` state file keyed by stable numeric ID
3. State file writes survive Ctrl-C without corruption
4. Skip already-downloaded items on subsequent runs with a per-item skip message

</domain>

<decisions>
## Implementation Decisions

### State file format
- Location: `.bcdl/{username}.json`
- Key: `sale_item_id` as a string (stable numeric ID from Bandcamp API, tied to the purchase record)
- Value: minimal metadata object — `{ "artist": "...", "title": "...", "url": "...", "downloaded_at": "..." }`
- Example entry: `{ "12345678": { "artist": "Burial", "title": "Untrue", "url": "https://...", "downloaded_at": "2026-03-19T14:23:00" } }`

### State write timing
- Write to state **after successful download only** (yt-dlp exit code 0)
- Failed items are NOT recorded — they will be retried on the next run
- Corrupt/partial state from Ctrl-C must not happen — use atomic write (write to temp file, then rename)

### Skip output
- One line per skipped item: `[skip] Artist — Title`
- Visually distinct from download lines (which use `[N/M] Artist — Title` format)
- No change to the existing download line format

### yt-dlp detection
- Check at **startup, before fetching the collection** — fail fast, no wasted network calls
- Detection method: `shutil.which("yt-dlp")` or attempt `subprocess.run(["yt-dlp", "--version"], ...)` — researcher to confirm best approach
- Error message (exact): `Error: yt-dlp is not installed. Install it with: pip install yt-dlp`
- Exit with non-zero code after printing this message

### Claude's Discretion
- Atomic write implementation (write-then-rename pattern using `tempfile` + `os.replace`)
- Whether StateManager is a class or a set of functions
- Where StateManager lives (same file or new module) — keep it simple for a 186-line codebase
- Exact `downloaded_at` timestamp format (ISO 8601 recommended)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — RESM-01 is the requirement this phase satisfies; RELY-01 is out of scope for this phase

### Roadmap
- `.planning/ROADMAP.md` — Phase 1 success criteria (4 items) define exactly what must be TRUE; do not reinterpret

No external specs — requirements are fully captured in decisions above and roadmap success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `download_item()` in `bcdl.py:97` — current download function; needs to be called by a loop that checks state before invoking and writes state after success
- `main()` in `bcdl.py:120` — entry point; yt-dlp check and state initialization go here before the download loop
- `subprocess.run(cmd)` at `bcdl.py:116` — currently bare; `FileNotFoundError` is what Python raises when yt-dlp is missing

### Established Patterns
- Tests use `unittest.mock.patch` + `pytest` — new StateManager should be patchable the same way
- `main()` is currently untested — Phase 1 adds testable state logic; tests for new state behavior should be added
- Error handling in `main()` catches `requests.HTTPError` and `ValueError` and calls `sys.exit(1)` — yt-dlp check should follow the same pattern

### Integration Points
- `main()` is the sole integration point — StateManager is initialized here, checked before download, written after success
- `.bcdl/` directory must be created if it doesn't exist (no assumption about pre-existing dir)

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-state-foundation*
*Context gathered: 2026-03-19*
