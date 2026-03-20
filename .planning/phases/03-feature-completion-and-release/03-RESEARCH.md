# Phase 3: Feature Completion and Release - Research

**Researched:** 2026-03-20
**Domain:** CLI flag implementation, packaging (hatchling/pipx), GitHub Actions CI, technical documentation
**Confidence:** HIGH

## Summary

Phase 3 adds the `--format` flag for audio format selection, rewrites the README for non-developer users, verifies the wheel builds and installs correctly via pipx, and adds GitHub Actions CI. All three work areas are straightforward: the format flag is a thin argparse extension that appends `-x --audio-format <name>` to the yt-dlp command list; hatchling/uv already produce a valid wheel today (verified); and `astral-sh/setup-uv@v7` with `uv sync` + `uv run pytest` is the current idiomatic CI pattern. The README is a full rewrite — the existing file is developer-only; the new one must be pipx-first with a cookies walkthrough.

**Primary recommendation:** Implement `--format` flag first (code change), then README rewrite (prose), then wheel smoke-test verification (manual step), and finally GitHub Actions YAML (infra). Each is independently testable and has no inter-dependencies.

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Accept friendly names only: `flac`, `mp3`, `wav`, `aac`, `opus` — validate on input, error on unrecognized value
- Translate to yt-dlp's `-x --audio-format <name>` flags internally (not raw passthrough)
- Default: no `--audio-format` flag passed — yt-dlp picks best available format (matches current behavior)
- Flag position: anywhere — standard argparse behavior, no special ordering required
- `--format` on `--export-csv` runs: silently ignored (CSV export doesn't download)
- Error message on invalid format: `Error: unsupported format 'xyz'. Choose from: flac, mp3, wav, aac, opus`
- Exit non-zero on invalid format, before fetching the collection (fail fast)
- Primary install path: `pipx install bcdl` — top of README
- uv + git clone moves to a "For contributors / Development" section at the bottom
- Cookies workflow: step-by-step with "Get cookies.txt LOCALLY" Chrome extension, exact export steps
- Skip/resume behavior: brief section explaining state file at `.bcdl/{username}.json`
- Retry behavior: short "how it works" note explaining `[ N/M] Artist — Title: OK/FAILED` format
- Every current flag documented with a concrete usage example: `--cookies`, `--delay`, `--export-csv`, `--format`
- Build wheel locally with hatchling (`uv build` or `python -m build`)
- Install from local wheel with pipx (`pipx install dist/bcdl-*.whl`)
- Verify `bcdl --help` runs correctly from a clean environment
- No PyPI publish in this phase
- `.github/workflows/ci.yml` — run `pytest` on push and pull_request to `main`
- Matrix: Python 3.12 only
- Use `pip install -e .[dev]` or `uv sync` to install dev deps before running tests
- No new code needed for resume — Phase 1 fully implemented it; Phase 3 only documents it

### Claude's Discretion
- Exact set of yt-dlp flags used for audio extraction (e.g. whether to also pass `--extract-audio`)
- README section ordering and exact prose
- CI workflow caching strategy (pip cache / uv cache)
- Whether to add `bcdl` version to `--help` output (via `pyproject.toml` version field)

### Deferred Ideas (OUT OF SCOPE)
- `--output-dir` flag (DCTL-02) — v2 scope
- `--no-resume` / `--reset` flags — v2 scope
- Arbitrary yt-dlp format strings passthrough
- PyPI publish
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DCTL-01 | User can specify audio format via `--format` flag (e.g. `flac`, `mp3`) passed through to yt-dlp | yt-dlp `-x --audio-format` flags confirmed; argparse pattern established in bcdl.py; `--format` validation before network call follows existing yt-dlp detection pattern |
| DOCS-01 | README documents all flags with usage examples and install instructions clear enough for a non-developer Bandcamp user | Existing README is developer-only; full rewrite required; pipx install pattern confirmed; cookies workflow identified |
</phase_requirements>

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| argparse | stdlib | `--format` flag parsing | Already used in `main()`; no new dependency |
| yt-dlp | system dep | Audio format extraction via `-x --audio-format` | The project's download engine; flags confirmed in current docs |
| hatchling | build dep | Wheel building | Already in `pyproject.toml` `[build-system]`; `uv build --wheel` produces valid wheel today |
| pipx | user tool | Isolated CLI install | Standard for CLI tools; handles PATH, venv isolation; install from wheel path supported |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| astral-sh/setup-uv | @v7 (GH Action) | Install uv in CI | GitHub Actions workflow only |
| actions/checkout | @v4 | Checkout repo in CI | GitHub Actions workflow only |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uv sync` in CI | `pip install -e .[dev]` | `uv sync` is faster and respects lockfile; `pip install -e .[dev]` works but doesn't use uv cache. CONTEXT.md permits either — `uv sync` is recommended |
| `astral-sh/setup-uv@v7` | `actions/setup-python` + pip | setup-uv handles both Python and uv install in one step; simpler YAML |

**Installation (project already has these, no new dependencies):**
```bash
# For users:
pipx install dist/bcdl-0.1.0-py3-none-any.whl

# Build wheel:
uv build --wheel
```

**Version verification (confirmed 2026-03-20):**
- `uv build --wheel` produces `dist/bcdl-0.1.0-py3-none-any.whl` — verified working in this repo
- `astral-sh/setup-uv@v7` — current version per official docs as of March 2026
- Python 3.12 — confirmed as project venv version (`3.12.12`)

## Architecture Patterns

### Recommended Project Structure
No new directories needed. Changes touch:
```
bcdl.py                           # --format flag + download_with_retry signature change
README.md                         # full rewrite
.github/
└── workflows/
    └── ci.yml                    # new file
```

### Pattern 1: Format Flag — Argparse + Conditional cmd Extension

**What:** Add `--format` to argparse, validate against allowed set with `sys.exit(1)` on unknown value, append `-x --audio-format <name>` to the yt-dlp `cmd` list inside `download_with_retry()` when format is not None.

**When to use:** Follows the exact same pattern as `--cookies` in the current code.

**Example:**
```python
# In main() — argparse setup (follows --delay pattern at bcdl.py:270)
SUPPORTED_FORMATS = ("flac", "mp3", "wav", "aac", "opus")

parser.add_argument(
    "--format",
    metavar="FORMAT",
    help=f"Audio format for downloads ({', '.join(SUPPORTED_FORMATS)})",
)

# Validation — after shutil.which check, before get_all_collection_items
if args.format is not None and args.format not in SUPPORTED_FORMATS:
    print(
        f"Error: unsupported format '{args.format}'. "
        f"Choose from: {', '.join(SUPPORTED_FORMATS)}",
        file=sys.stderr,
    )
    sys.exit(1)

# Pass through to download_with_retry:
success, reason = download_with_retry(
    item, i, len(items),
    cookies_file=args.cookies,
    audio_format=args.format,   # None when not specified
)
```

```python
# In download_with_retry() — cmd extension (follows --cookies pattern at bcdl.py:201)
def download_with_retry(
    item: dict,
    index: int,
    total: int,
    cookies_file: str | None = None,
    audio_format: str | None = None,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> tuple[bool, str]:
    ...
    cmd = ["yt-dlp", "--quiet", "--no-progress", url]
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    if audio_format:
        cmd += ["-x", "--audio-format", audio_format]
    ...
```

**Critical note on yt-dlp flags:** `-x` (`--extract-audio`) is REQUIRED in addition to `--audio-format`. The yt-dlp docs state `--audio-format` operates only as a modifier for `-x`. Omitting `-x` means `--audio-format` is silently ignored. Source: yt-dlp README, confirmed March 2026.

**Also requires ffmpeg:** Audio extraction (`-x`) requires `ffmpeg` and `ffprobe` on the system. This is a yt-dlp requirement, not something bcdl controls. The README should note this as a prerequisite alongside yt-dlp.

### Pattern 2: `uv build --wheel` for Packaging

**What:** Run `uv build --wheel` in the project root. Produces `dist/bcdl-{version}-py3-none-any.whl`.

**Verified output (2026-03-20):**
```
Building wheel...
Successfully built dist/bcdl-0.1.0-py3-none-any.whl
```

Wheel contents confirmed correct: `bcdl.py`, `bcdl-0.1.0.dist-info/entry_points.txt` (contains `bcdl = bcdl:main`).

### Pattern 3: GitHub Actions CI with uv

**What:** Single workflow file triggering on push/PR to main, using `astral-sh/setup-uv@v7`.

**Example:**
```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
```

**Notes:**
- No `python-version` matrix needed — CONTEXT.md says Python 3.12 only; `pyproject.toml` has `requires-python = ">=3.12"` and `uv` will pick the correct interpreter.
- `enable-cache: true` caches the uv download cache between runs at no complexity cost.
- `uv sync` installs both runtime and dev deps (including pytest) from the `[dependency-groups] dev` table in `pyproject.toml`.

### Anti-Patterns to Avoid

- **Passing `--audio-format` without `-x`:** yt-dlp silently ignores `--audio-format` when `-x` is not present. Always include both flags together.
- **Using glob `dist/bcdl-*.whl` in pipx install:** Works in bash but can match stale wheels if multiple versions exist in `dist/`. Prefer explicit path or `uv build --wheel --clear` to clean first.
- **Adding `pipx` as a Python dependency:** pipx is a user tool installed separately (e.g. `brew install pipx`), not a project dependency. Do not add it to `pyproject.toml`.
- **Skipping yt-dlp detection before format validation:** The current code checks `shutil.which("yt-dlp")` then exits. Format validation should come immediately after this check — fail fast before network calls.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Audio format conversion | Custom ffmpeg subprocess wrapper | yt-dlp `-x --audio-format` | yt-dlp handles format negotiation, ffmpeg invocation, and error handling |
| Wheel building | Custom `setup.py` or `MANIFEST.in` | `uv build --wheel` (hatchling already configured) | hatchling is already in `pyproject.toml`; `uv build` works today |
| CLI isolation for testing | System-wide install | pipx from local wheel | Provides clean environment isolation identical to what end users get |
| CI Python setup | Manual pyenv/deadsnakes | `astral-sh/setup-uv@v7` | Installs uv and Python in one step; handles caching |

**Key insight:** Every packaging and CI operation in this phase has an existing, working tool. No custom scripts needed.

## Common Pitfalls

### Pitfall 1: `-x` flag omitted from audio extraction
**What goes wrong:** `yt-dlp --audio-format flac URL` downloads the video in its native container but does NOT extract or convert audio. The `--audio-format` flag is silently ignored without `-x`.
**Why it happens:** The flags are documented as a pair but people assume `--audio-format` is sufficient.
**How to avoid:** Always append both `["-x", "--audio-format", audio_format]` as a pair. Test by checking that the downloaded file has the expected extension (`.flac`, `.mp3`, etc.).
**Warning signs:** Downloads "succeed" but produce `.webm` or `.mp4` files instead of audio files.

### Pitfall 2: ffmpeg not installed when `--format` is used
**What goes wrong:** yt-dlp exits with an error like `ERROR: ffmpeg not found. Please install or provide the path using --ffmpeg-location` when `-x` is passed.
**Why it happens:** Audio extraction requires ffmpeg; yt-dlp itself doesn't bundle it.
**How to avoid:** README should list ffmpeg as a prerequisite alongside yt-dlp when using `--format`. bcdl should NOT try to detect ffmpeg — let yt-dlp surface the error naturally (it's clear and actionable).
**Warning signs:** `FAILED (ffmpeg not found)` in download output when `--format` is specified.

### Pitfall 3: pipx install from stale wheel in `dist/`
**What goes wrong:** `pipx install dist/bcdl-*.whl` installs an old build if multiple versions exist in `dist/`. The glob matches the first alphabetically, which may not be the latest.
**Why it happens:** `uv build` appends new wheels rather than replacing by default.
**How to avoid:** Run `uv build --wheel --clear` to remove stale artifacts before building, then use the explicit wheel path. Or use `pipx install --force dist/bcdl-0.1.0-py3-none-any.whl` with the known version string.
**Warning signs:** `bcdl --version` (if added) shows old version number.

### Pitfall 4: `uv sync` in CI does not install yt-dlp
**What goes wrong:** Tests that call yt-dlp as a subprocess fail in CI because yt-dlp is not installed on the runner. Tests that mock `_run_yt_dlp` or `subprocess.run` pass correctly.
**Why it happens:** yt-dlp is a system-level tool dependency, not a Python package dependency in `pyproject.toml`.
**How to avoid:** All tests for download behavior should mock `_run_yt_dlp` or `subprocess.run` at the appropriate layer. Do NOT add yt-dlp to `pyproject.toml` dependencies — it's a runtime system requirement. The existing test suite already follows this pattern correctly.
**Warning signs:** CI tests pass locally but fail in GitHub Actions with "No such file or directory: yt-dlp".

### Pitfall 5: `--format` flag name conflicts with Python built-in
**What goes wrong:** No conflict at the argparse level — argparse stores it as `args.format`. However, `format` is a Python built-in name. Avoid shadowing it with a local variable named `format` inside functions.
**How to avoid:** Reference the argument as `args.format` in `main()` and pass it as `audio_format=args.format` to `download_with_retry()`. Use `audio_format` as the parameter name everywhere inside the call chain.

### Pitfall 6: GitHub Actions YAML indentation errors
**What goes wrong:** YAML is whitespace-sensitive. A misindented step causes the workflow to fail silently or with a confusing parse error.
**How to avoid:** Validate YAML syntax locally with `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` before committing. GitHub also validates syntax on push and shows errors in the Actions tab.

## Code Examples

### --format flag: complete cmd construction
```python
# Source: pattern derived from bcdl.py:200-202 (--cookies pattern)
cmd = ["yt-dlp", "--quiet", "--no-progress", url]
if cookies_file:
    cmd += ["--cookies", cookies_file]
if audio_format:
    cmd += ["-x", "--audio-format", audio_format]
```

### --format validation in main()
```python
# Source: pattern derived from bcdl.py:280-285 (yt-dlp detection pattern)
SUPPORTED_FORMATS = ("flac", "mp3", "wav", "aac", "opus")

# After shutil.which check, before get_all_collection_items:
if args.format is not None and args.format not in SUPPORTED_FORMATS:
    print(
        f"Error: unsupported format '{args.format}'. "
        f"Choose from: {', '.join(SUPPORTED_FORMATS)}",
        file=sys.stderr,
    )
    sys.exit(1)
```

### Building and installing the wheel
```bash
# Source: verified locally 2026-03-20
uv build --wheel --clear
pipx install dist/bcdl-0.1.0-py3-none-any.whl
bcdl --help
```

### GitHub Actions ci.yml (complete)
```yaml
# Source: https://docs.astral.sh/uv/guides/integration/github/ (verified March 2026)
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v7
        with:
          enable-cache: true
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `setup.py` + `python setup.py bdist_wheel` | `pyproject.toml` + `uv build --wheel` | PEP 517/518 (2018), uv widespread 2024 | Simpler, no `setup.py` needed |
| `actions/setup-python` + `pip install` | `astral-sh/setup-uv@v7` + `uv sync` | 2024 | Faster installs, built-in caching |
| `pip install -r requirements.txt` in CI | `uv sync` from `pyproject.toml` | 2024 | Single source of truth, lockfile-aware |

**Deprecated/outdated:**
- `setup.py bdist_wheel`: replaced by `uv build` / `python -m build` with hatchling backend
- `pip install -e ".[dev]"` in CI: still works but `uv sync` is preferred for uv-based projects

## Open Questions

1. **ffmpeg prerequisite detection**
   - What we know: yt-dlp surfaces a clear error if ffmpeg is missing when `-x` is used
   - What's unclear: Should bcdl detect ffmpeg presence and warn before calling yt-dlp?
   - Recommendation: No — let yt-dlp handle it. The error message is clear. Adding a second ffmpeg check in bcdl adds complexity for little user benefit. README note is sufficient.

2. **`--format` behavior when format is unavailable on Bandcamp**
   - What we know: yt-dlp requests the format from Bandcamp; if FLAC isn't available, yt-dlp may fall back or fail
   - What's unclear: Exact yt-dlp behavior when Bandcamp doesn't offer the requested format
   - Recommendation: Document in README that "FLAC where available" is the expected behavior. yt-dlp handles format negotiation; bcdl passes the flag through and surfaces any resulting error via the existing `FAILED` output path. No special handling needed.

3. **`bcdl --version` in `--help` output**
   - What we know: `pyproject.toml` has `version = "0.1.0"`; argparse supports `action="version"` with `version="%(prog)s 0.1.0"`
   - What's unclear: Whether to hardcode or read from package metadata at runtime
   - Recommendation (Claude's discretion): Add `parser.add_argument("--version", action="version", version="bcdl 0.1.0")` as a hardcoded string. Using `importlib.metadata.version("bcdl")` is more correct but adds complexity for a v0.1.0 tool. Revisit in v2.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (in `[dependency-groups] dev`) |
| Config file | none — pytest discovers `tests/` automatically |
| Quick run command | `uv run pytest tests/test_bcdl.py -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DCTL-01 | `--format flac` appends `-x --audio-format flac` to yt-dlp cmd | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag -x -q` | ❌ Wave 0 |
| DCTL-01 | `--format mp3` appends `-x --audio-format mp3` to yt-dlp cmd | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag -x -q` | ❌ Wave 0 |
| DCTL-01 | `--format xyz` exits non-zero with correct error message | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag::test_invalid_format_exits -x -q` | ❌ Wave 0 |
| DCTL-01 | default (no `--format`) does NOT append `-x` or `--audio-format` | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag::test_no_format_no_flags -x -q` | ❌ Wave 0 |
| DCTL-01 | `--format` with `--export-csv` silently ignored (no `-x` in cmd) | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag::test_format_ignored_with_csv -x -q` | ❌ Wave 0 |
| DCTL-01 | format validation happens before network call | unit | `uv run pytest tests/test_bcdl.py::TestFormatFlag::test_format_validates_before_network -x -q` | ❌ Wave 0 |
| DOCS-01 | README contains all flags; `--format` section present | manual | n/a — review README.md content | n/a |
| DOCS-01 | `bcdl --help` output includes `--format` with description | smoke | `uv run python -c "import bcdl; import sys; sys.argv=['bcdl','--help']" 2>&1 \| grep format` | manual |

**Note on packaging tests:** The wheel build and pipx install verification are smoke tests run manually, not automated unit tests. They exercise the packaging toolchain rather than bcdl's logic.

```bash
# Packaging smoke test sequence (manual, run once per release):
uv build --wheel --clear
pipx install --force dist/bcdl-0.1.0-py3-none-any.whl
bcdl --help                          # verify entry point works
pipx uninstall bcdl                  # cleanup
```

**Note on GitHub Actions YAML validation:**
```bash
# Local YAML syntax validation (no GH account needed):
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML valid')"
```

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_bcdl.py -x -q` (< 15 seconds)
- **Per wave merge:** `uv run pytest` (full suite, currently ~10 seconds for 59 tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_bcdl.py::TestFormatFlag` class — covers DCTL-01 (all format flag behaviors above)

*(All other test infrastructure exists and is fully functional — 59 tests passing as of 2026-03-20)*

## Sources

### Primary (HIGH confidence)
- yt-dlp README (https://raw.githubusercontent.com/yt-dlp/yt-dlp/master/README.md) — audio extraction flags `-x`, `--audio-format`, supported formats, ffmpeg requirement
- `uv build --wheel` — verified locally in this repo (2026-03-20), produces correct wheel
- `tests/test_bcdl.py` — existing test patterns and fixtures, read directly
- `bcdl.py` — existing argparse setup, cmd construction pattern, validation pattern, read directly
- `pyproject.toml` — hatchling build-system, entry point, dev dependencies, read directly

### Secondary (MEDIUM confidence)
- https://docs.astral.sh/uv/guides/integration/github/ — `astral-sh/setup-uv@v7`, `uv sync`, `uv run pytest` CI pattern (official uv docs, verified March 2026)
- yt-dlp GitHub README WebSearch confirmation — supported formats: best, aac, alac, flac, m4a, mp3, opus, vorbis, wav

### Tertiary (LOW confidence)
- None — all critical claims verified with primary or secondary sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — hatchling/uv/argparse all verified locally; setup-uv from official docs
- Architecture: HIGH — format flag pattern directly mirrors existing --cookies code; uv build verified working
- Pitfalls: HIGH — `-x` requirement confirmed in official yt-dlp docs; others derived from direct code inspection

**Research date:** 2026-03-20
**Valid until:** 2026-06-20 (stable toolchain; yt-dlp flag API changes rarely)
