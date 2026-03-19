# Stack Research

**Domain:** Python CLI downloader tool (PyPI-distributable)
**Researched:** 2026-03-19
**Confidence:** MEDIUM — network tools are disabled; recommendations drawn from training knowledge (cutoff Aug 2025) cross-referenced against existing lockfile and codebase. Specific version pins are HIGH confidence for already-resolved packages, MEDIUM for new additions.

## Recommended Stack

### Core Technologies (Existing — Keep As-Is)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Python | 3.12+ | Runtime | Already required; modern union type syntax (`X \| Y`), `tomllib` stdlib, match statements. No reason to change. |
| uv | latest | Project manager, packaging | Already in use. Fastest resolver in Python ecosystem, generates `uv.lock` for reproducible builds, handles virtualenvs. Better than Poetry or pip-tools for new projects in 2025. |
| hatchling | latest | PyPI build backend | Already configured in `pyproject.toml`. PEP 517/518 compliant, no config boilerplate, handles `[project.scripts]` entry points correctly. pipx and pip both install from it cleanly. |
| requests | 2.x | HTTP client for Bandcamp API | Already in use. Correct choice here — the Bandcamp API calls are simple GET/POST, no streaming, no async. Adding httpx would be premature complexity. |
| beautifulsoup4 | 4.14.3 | HTML parsing | Already in use. Correct choice for scraping the embedded JSON blob from Bandcamp's HTML. |
| pytest | latest (via dev) | Test framework | Already in use. Standard. |

### New Additions — Production Hardening

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| rich | >=13.0,<14 | Progress display, console output, logging | See detailed rationale below. Standard for feature-rich CLI output in 2025. |
| tenacity | >=8.2,<9 | Retry logic with backoff | See detailed rationale below. Cleaner API than alternatives, actively maintained. |

---

## Decision Rationale

### Progress Display: rich (not tqdm)

**Recommendation: `rich`**

`tqdm` is appropriate for a single progress bar over an iterable. It breaks down when you need:
- Per-item status lines (artist — title: downloading / skipped / failed)
- A live summary panel showing running counts
- Clean suppression of subprocess stdout while displaying your own output
- Structured logging that doesn't corrupt the progress bar

`rich` solves all of this with `Progress`, `Live`, and `Console`. The key feature for bcdl specifically: `rich.Progress` can display a multi-column progress bar while `Console.log()` lines appear above it without corruption — this is the correct pattern for a downloader that needs to show both "N/M items" progress and per-item results.

`rich` also replaces the current `print()` calls with structured `Console` output that respects `NO_COLOR` and TTY detection. For users piping output to a file or running in CI, rich degrades gracefully.

**tqdm is not wrong** — it's simpler. Choose tqdm if progress display is the only change and the per-item logging is acceptable as raw print(). For this project's stated goals (rich progress display, success/fail summary), rich is the correct tool.

**Confidence: HIGH** — rich is the dominant production CLI library in the Python ecosystem as of 2025 (used by pip itself, uv, httpie, black, and most major Python CLI tools).

---

### State Tracking for Resume: JSON file (not SQLite, not shelve)

**Recommendation: Plain JSON file (`~/.config/bcdl/state.json` or `./bcdl-state.json`)**

Three options evaluated:

**JSON file** — A `Set[str]` of downloaded item IDs serialized to JSON.
- Human-readable, user can inspect/edit it
- Zero dependencies, stdlib `json` module
- Trivially portable (download directory can move, state file stays)
- Atomic write pattern (write to `.tmp`, then `os.replace()`) prevents corruption
- Adequate for this use case: lookup is O(n) but n is at most a few thousand items

**SQLite (`sqlite3` stdlib)** — Overkill. The data model is one flat set of strings ("which item IDs have been downloaded"). SQLite introduces schema migrations, connection management, and lock file issues for zero benefit. Use SQLite when you have relational data or need concurrent writes. This tool runs as a single sequential process.

**shelve** — Do not use. `shelve` uses `dbm` under the hood, which has platform-specific backends (ndbm, gdbm, dumbdbm). Files created on macOS may not open on Linux. Not portable. Not human-readable. No advantage over JSON for this scale.

**State file location strategy:** Default to `~/.local/share/bcdl/<username>/state.json` (XDG-compliant on Linux, reasonable on macOS). Allow override via `--state-file` flag. Keying by username lets multiple users share the same installation without collision.

**State file format:**
```json
{
  "version": 1,
  "downloaded": ["item_id_1", "item_id_2"],
  "last_run": "2026-03-19T14:00:00Z"
}
```

**Confidence: HIGH** — this is the standard pattern for single-user CLI resume state at this scale.

---

### Retry Logic: tenacity (not backoff, not manual)

**Recommendation: `tenacity >=8.2`**

Three options evaluated:

**tenacity** — Decorator-based retry with full control:
```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception(is_retryable_error),
    reraise=True,
)
def download_item(...):
    ...
```
- Handles exponential backoff with jitter
- Supports per-exception-type retry decisions (retry on 429/5xx, not on 404)
- `before_sleep` callback allows logging "retrying in Xs" to console
- Actively maintained, ~1M weekly downloads

**backoff** — Similar decorator API, lighter. Adequate but less expressive for complex retry conditions. No strong reason to prefer over tenacity.

**Manual `time.sleep()` loops** — The current approach (no retry). Works but clutters business logic with retry state management.

**What tenacity covers for bcdl:**
- HTTP 429 (rate limited) — retry with exponential backoff
- HTTP 5xx (server error) — retry up to 3x
- `requests.Timeout` — retry
- HTTP 404 — do NOT retry (item genuinely unavailable)
- yt-dlp non-zero exit — retry once, then mark as failed

**Confidence: MEDIUM** — tenacity is well-established but I cannot verify the exact latest version without network access. `>=8.2,<9` is a safe constraint based on the 8.x stable series.

---

### CLI Argument Parsing: argparse (keep existing)

**Recommendation: Keep `argparse`**

The existing `argparse` implementation is correct and complete for the current feature set. Do not migrate to click or typer.

**click** — Better ergonomics for complex CLIs with subcommands, parameter types, and decorators. Overkill for a single-command tool with 4-5 flags.

**typer** — Built on click, adds type annotation-based declaration. Attractive but adds a dependency and requires restructuring the existing working code for no functional gain.

**argparse** — Stdlib, zero dependencies, already works. Add new flags (`--format`, `--filter-artist`, `--state-file`) as the project grows. Only migrate to click/typer if subcommands (e.g., `bcdl download`, `bcdl export`, `bcdl status`) become necessary.

**Confidence: HIGH**

---

### PyPI Distribution: hatchling + pipx (keep existing)

**Recommendation: Keep hatchling, document pipx as primary install method**

The `pyproject.toml` already has the entry point configured correctly:
```toml
[project.scripts]
bcdl = "bcdl:main"
```

This means `pip install bcdl` and `pipx install bcdl` both work immediately once published to PyPI. No changes needed to the build system.

**pipx vs pip for users:** Recommend `pipx install bcdl` in the README as the primary install method. pipx installs CLI tools in isolated virtualenvs, preventing dependency conflicts with user's system Python. This is the 2025 standard for distributing Python CLI tools.

**Versioning:** Use `hatch version` to manage version bumps, or simply edit `pyproject.toml` manually. No need for `bumpversion` or `bump2version` at this scale.

**Confidence: HIGH**

---

### What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `tqdm` | Can't handle multi-line status output without corruption; no structured logging | `rich` |
| `sqlite3` for state | Relational overkill for a flat set of strings; portability issues | JSON file with atomic write |
| `shelve` | Platform-dependent backend; not portable between macOS/Linux | JSON file |
| `httpx` | Async HTTP client; bcdl's API calls are sequential, no async needed | Keep `requests` |
| `click` or `typer` | Unnecessary migration cost; `argparse` is adequate for single-command CLIs | Keep `argparse` |
| `pydantic` | Data validation library; collection items are dicts from Bandcamp API, not complex models | Plain `dict` with `.get()` |
| `loguru` | Logging library; `rich`'s `Console.log()` is adequate for a CLI tool | `rich.Console` |
| `backoff` | Similar to tenacity but less expressive; redundant if tenacity chosen | `tenacity` |

---

## Supporting Libraries (Development)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | latest | Test runner | Already in use. Continue. |
| pytest-cov | latest | Coverage reports | Add when CI is configured; `uv add --dev pytest-cov` |
| responses | latest | Mock `requests` in tests | Add to mock Bandcamp API calls without network; cleaner than `unittest.mock.patch` for HTTP |
| ruff | latest | Linter + formatter | Replaces flake8 + black in one tool; `uv add --dev ruff` |

---

## Installation

```bash
# Add production dependencies
uv add rich tenacity

# Add dev dependencies
uv add --dev pytest-cov responses ruff

# Install for local development
uv sync

# Install via pipx (end-user)
pipx install bcdl

# Install from local checkout
pipx install .
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| `rich` | `tqdm` | Single progress bar over one iterable, no per-item status logging needed |
| JSON state file | SQLite | If you needed to query state by multiple fields (date, artist, format), or if concurrent processes wrote state |
| `tenacity` | `backoff` | Either works; backoff is lighter if tenacity's composable stop/wait/retry conditions feel like overkill |
| `argparse` | `click` / `typer` | When adding subcommands or when decorator-style argument declaration is preferred by the team |
| `hatchling` | `setuptools` | Setuptools is still widely used but hatchling is cleaner; no migration needed since project already uses hatchling |

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| `rich >=13` | Python 3.12+ | rich 13.x+ requires Python 3.7+; no conflicts |
| `tenacity >=8.2` | Python 3.12+ | tenacity 8.x requires Python 3.6+; no conflicts |
| `requests 2.x` | `certifi 2026.x` | Already co-installed in lockfile, compatible |
| `beautifulsoup4 4.14.x` | Python 3.12+ | No conflicts |

---

## Sources

- Existing lockfile (`uv.lock`) — confirmed beautifulsoup4 4.14.3, certifi 2026.2.25, charset-normalizer 3.4.6 (HIGH confidence — locked versions)
- Existing `pyproject.toml` — confirmed hatchling build backend, entry point configuration (HIGH confidence)
- Existing `bcdl.py` — confirmed argparse usage, subprocess pattern for yt-dlp, no retry/state logic (HIGH confidence)
- Training knowledge (cutoff Aug 2025) — rich vs tqdm comparison, tenacity API, JSON state pattern, pipx distribution pattern (MEDIUM confidence — cannot verify against live PyPI)
- Note: WebSearch, WebFetch, and Brave Search were unavailable during this research session. Version ranges are conservative (`>=X.Y,<NEXT_MAJOR`) to allow uv to resolve the latest compatible release.

---

*Stack research for: Python CLI downloader (bcdl — Bandcamp collection downloader)*
*Researched: 2026-03-19*
