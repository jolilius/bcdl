# Phase 3: Feature Completion and Release - Context

**Gathered:** 2026-03-20
**Status:** Ready for planning

<domain>
## Phase Boundary

Add `--format` flag for audio format selection, write a non-developer-friendly README (pipx as primary install path, full cookies walkthrough, output behavior explained), and verify the package builds and installs correctly via pipx. Add a minimal GitHub Actions CI workflow. Resume behavior is already fully implemented — Phase 3 only documents it.

Out of scope: `--output-dir`, `--no-resume`, `--reset`, PyPI publish, retry configurability.

</domain>

<decisions>
## Implementation Decisions

### Format flag
- Accept friendly names only: `flac`, `mp3`, `wav`, `aac`, `opus` — validate on input, error on unrecognized value
- Translate to yt-dlp's `-x --audio-format <name>` flags internally (not raw passthrough)
- Default: no `--audio-format` flag passed — yt-dlp picks best available format (matches current behavior)
- Flag position: anywhere — standard argparse behavior, no special ordering required
- `--format` on `--export-csv` runs: silently ignored (CSV export doesn't download)
- Error message on invalid format: `Error: unsupported format 'xyz'. Choose from: flac, mp3, wav, aac, opus`
- Exit non-zero on invalid format, before fetching the collection (fail fast, consistent with yt-dlp detection)

### README structure and audience
- Primary install path: `pipx install bcdl` — top of README, no uv/virtualenv required
- uv + git clone moves to a "For contributors / Development" section at the bottom
- Cookies workflow: step-by-step with specific browser extension named ("Get cookies.txt LOCALLY" Chrome extension), exact steps to export Netscape-format cookies
- Skip/resume behavior: brief section — explain that already-downloaded items are skipped automatically, state file lives at `.bcdl/{username}.json`, Ctrl-C is safe (run picks up where it left off)
- Retry behavior: short "how it works" note explaining the `[ N/M] Artist — Title: OK/FAILED` output format and that transient failures are auto-retried up to 3 times
- Every current flag documented with a concrete usage example in the options table: `--cookies`, `--delay`, `--export-csv`, `--format`

### Packaging scope
- Build wheel locally with hatchling (`uv build` or `python -m build`)
- Install from local wheel with pipx (`pipx install dist/bcdl-*.whl`)
- Verify `bcdl --help` runs correctly from a clean environment
- No PyPI publish in this phase

### GitHub Actions CI
- Add `.github/workflows/ci.yml` — run `pytest` on push and pull_request to `main`
- Matrix: Python 3.12 only (matches requires-python in pyproject.toml)
- Use `pip install -e .[dev]` or `uv sync` to install dev deps before running tests

### Resume wiring
- No new code needed — Phase 1 fully implemented state tracking and skip logic
- Phase 3 only: document the behavior clearly in the README

### Claude's Discretion
- Exact set of yt-dlp flags used for audio extraction (e.g. whether to also pass `--extract-audio`)
- README section ordering and exact prose
- CI workflow caching strategy (pip cache / uv cache)
- Whether to add `bcdl` version to `--help` output (via `pyproject.toml` version field)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements
- `.planning/REQUIREMENTS.md` — DCTL-01 (format flag, v1, this phase), DOCS-01 (README, v1, this phase), DIST-01/DIST-02 (packaging/CI, v2 but partially in scope here per discussion)

### Roadmap
- `.planning/ROADMAP.md` — Phase 3 success criteria (3 items) define exactly what must be TRUE

### Prior phase decisions
- `.planning/phases/01-state-foundation/01-CONTEXT.md` — state file format, skip line format `[skip] Artist — Title`, error pattern (`sys.exit(1)` + stderr)
- `.planning/phases/02-download-reliability/02-CONTEXT.md` — status line format `[N/M] Artist — Title: OK/FAILED`, retry verbosity, summary format

No external specs — requirements are fully captured in decisions above and roadmap success criteria.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `argparse` setup in `main()` at `bcdl.py:261` — `--format` added here, same pattern as `--cookies` and `--delay`
- `download_with_retry()` at `bcdl.py:183` — `cookies_file` parameter shows how to thread a new flag through; `--format` follows the same pattern
- `shutil.which("yt-dlp")` check at `bcdl.py:284` — `--format` validation happens right after this, before `get_all_collection_items()`
- `pyproject.toml` — entry point `bcdl = "bcdl:main"` and `hatchling` build backend already configured; `uv build` should work out of the box

### Established Patterns
- Flag validation pattern: `print(msg, file=sys.stderr)` + `sys.exit(1)` — used for yt-dlp check; format validation follows same pattern
- `download_with_retry` cmd list built as `["yt-dlp", "--quiet", "--no-progress", url]` with conditional `--cookies` appended — `--audio-format <fmt>` and `-x` flags appended the same way when `--format` is set

### Integration Points
- `download_with_retry()` signature will gain a `format: str | None = None` parameter
- `main()` passes `format=args.format` through to `download_with_retry()` (same as `cookies_file=args.cookies`)
- README replaces the current uv-first install section with pipx as primary

</code_context>

<specifics>
## Specific Ideas

No specific references or "I want it like X" moments — open to standard approaches within the decisions above.

</specifics>

<deferred>
## Deferred Ideas

- `--output-dir` flag (DCTL-02) — v2 scope, not Phase 3
- `--no-resume` / `--reset` flags — v2 scope
- Arbitrary yt-dlp format strings passthrough — not needed; friendly names cover the common cases
- PyPI publish — out of scope for Phase 3; local build verification is sufficient

</deferred>

---

*Phase: 03-feature-completion-and-release*
*Context gathered: 2026-03-20*
