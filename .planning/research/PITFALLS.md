# Pitfalls Research

**Domain:** Python CLI downloader — scraping, subprocess orchestration, resume/retry, PyPI packaging
**Researched:** 2026-03-19
**Confidence:** HIGH (codebase directly inspected; patterns are well-established in Python packaging and CLI tooling)

---

## Critical Pitfalls

### Pitfall 1: State File Corruption on Interrupted Write

**What goes wrong:**
The resume state file (tracking which items have been downloaded) is written with a plain `open(..., "w")` and `json.dump()`. If the process is killed mid-write (Ctrl-C, OOM, power loss), the file is left truncated and invalid JSON. On the next run, the JSON parse fails and the user sees a confusing crash — or worse, silently starts from scratch because the error is swallowed.

**Why it happens:**
Developers add state persistence as an afterthought. The naive pattern (`open/write/close`) has a window where the file is partially written. The crash case is never tested because it requires simulating a kill mid-write.

**How to avoid:**
Write state atomically: write to a `.tmp` file, then `os.replace()` (which is atomic on POSIX). Always wrap state file reads in `try/except (json.JSONDecodeError, OSError)` with a clear user message and a fallback to empty state. Never silently ignore a corrupt state file — warn and offer `--reset-state`.

**Warning signs:**
- State file write happens inside the download loop without a `try/finally`
- No test for what happens when state file is malformed
- Recovery path is `sys.exit(1)` rather than "treating as empty + warn"

**Phase to address:**
Resume/checkpoint implementation phase (whichever phase introduces the state file).

---

### Pitfall 2: State File Keyed on Mutable Fields

**What goes wrong:**
The state file records completed downloads using a mutable field as the key — most commonly `album_title` or `artist + title`. Bandcamp item titles and band names can change (artist renames, reissues, title corrections). When the title changes, the state key no longer matches and the item re-downloads.

**Why it happens:**
Titles feel like natural identifiers. The stable, Bandcamp-internal identifier (`tralbum_id` or the numeric ID embedded in `item_url`) is buried in the API response and easy to overlook.

**How to avoid:**
Key the state on the stable numeric ID. The Bandcamp collection API returns a dict keyed by item ID (visible in the `item_cache.collection` structure already scraped). Use that dict key, or extract the numeric ID from `item_url` as a fallback. Record the title alongside the ID for human readability, but never use the title as the lookup key.

**Warning signs:**
- State file stores `"Artist — Title": true` instead of `"12345678": {...}`
- No test asserting that a title change does not cause a re-download

**Phase to address:**
Resume/checkpoint implementation phase.

---

### Pitfall 3: yt-dlp Subprocess stdout Flooding Progress Display

**What goes wrong:**
When Rich progress bars (or any terminal progress display) are added, yt-dlp's own output — printed directly to the terminal because `subprocess.run(cmd)` inherits stdout/stderr — overwrites and corrupts the progress display. Lines from yt-dlp interleave with progress bar updates, producing garbled output.

**Why it happens:**
`subprocess.run(cmd)` with no capture arguments inherits the parent's file descriptors. This works fine in a plain-print CLI but is incompatible with any library that owns the terminal (Rich, curses, tqdm).

**How to avoid:**
When a progress display is active, route yt-dlp output: either capture it fully (`capture_output=True`) and log it to a file/show on failure, or use `subprocess.PIPE` and stream it to a Rich `Live` layout panel. The current code already returns `result.returncode` — capturing output only requires adding `capture_output=True` to `subprocess.run()`. Log yt-dlp output on failure so the user can diagnose errors.

**Warning signs:**
- Progress library is added but `subprocess.run(cmd)` line is unchanged
- No test verifying that yt-dlp stderr is captured on non-zero exit

**Phase to address:**
Progress display phase AND subprocess error capture (these should ship together, not separately).

---

### Pitfall 4: PyPI Package Name Collision / Name Squatting

**What goes wrong:**
The package name `bcdl` may already be registered on PyPI by another project. Running `pip install bcdl` installs someone else's package. The `[project.scripts]` entry point `bcdl = "bcdl:main"` would then conflict.

**Why it happens:**
Short, obvious names for popular-domain tools get registered early. "bcdl" is short enough to be plausible as a pre-existing package.

**How to avoid:**
Check PyPI before any publishing phase: `pip index versions bcdl` or visit `pypi.org/project/bcdl`. If taken, choose a unique name (e.g., `bcdl-downloader`, `bandcamp-bcdl`). Update both `pyproject.toml` `[project] name` and the entry point mapping. The entry point command (`bcdl`) can remain `bcdl` even if the package name changes.

**Warning signs:**
- `twine upload` or `uv publish` fails with "name already taken"
- Checking PyPI is not part of the packaging phase checklist

**Phase to address:**
PyPI packaging phase — verify name availability before building the distribution.

---

### Pitfall 5: `yt-dlp` Not in PATH When Installed via pipx

**What goes wrong:**
`pipx install bcdl` installs `bcdl` in an isolated virtual environment. `yt-dlp` is listed as a user-installed external dependency, not a Python package dependency in `pyproject.toml`. When bcdl runs `subprocess.run(["yt-dlp", ...])`, it searches `PATH` — but pipx's isolated env does not expose the user's system `yt-dlp`. On some systems (especially fresh installs), `yt-dlp` is not on `PATH` at all and the error message is `FileNotFoundError: [Errno 2] No such file or directory: 'yt-dlp'`.

**Why it happens:**
The intentional design is to keep yt-dlp external (so it updates independently), but this means installation instructions are the only safety net. The error Python raises when `subprocess.run` can't find the executable is not user-friendly.

**How to avoid:**
Add a startup check: before the download loop, call `shutil.which("yt-dlp")` and fail fast with a clear message ("yt-dlp not found — install it with: pip install yt-dlp OR pipx install yt-dlp"). This converts a mid-run FileNotFoundError into an immediate, actionable message. Document the yt-dlp requirement prominently in README and in `--help` output.

**Warning signs:**
- No `shutil.which("yt-dlp")` check in `main()` before the download loop
- `FileNotFoundError` from `subprocess.run` is not caught anywhere

**Phase to address:**
Subprocess error capture phase; also verify in packaging/README phase.

---

### Pitfall 6: Retry Logic That Retries Non-Retryable Errors

**What goes wrong:**
Retry logic is added with a blanket `except Exception: retry` pattern. This retries 404s (item deleted from Bandcamp), authentication failures (expired/missing cookies), and malformed JSON — none of which will ever succeed on retry. The user waits through multiple retry cycles for errors that are permanent.

**Why it happens:**
Retry logic is copied from generic patterns without filtering by error type. HTTP status codes have clear retry semantics that are easy to overlook.

**How to avoid:**
Only retry on genuinely transient errors: `requests.exceptions.ConnectionError`, `requests.exceptions.Timeout`, and HTTP 429 / 5xx responses. Never retry 4xx errors (except 429). For yt-dlp subprocess failures, retry only when stderr contains network-related messages (connection reset, timeout), not when it contains "HTTP Error 404" or "Sign in to confirm your age". Implement exponential backoff with jitter for API retries (start at 2s, cap at 60s).

**Warning signs:**
- `except Exception` wraps the retry block rather than specific exception types
- 404 responses trigger the same retry path as 503 responses
- No test asserting that a 404 does NOT retry

**Phase to address:**
Retry logic implementation phase.

---

### Pitfall 7: Bandcamp HTML Scrape Breaks Silently After DOM Change

**What goes wrong:**
The initial collection fetch parses `soup.find("div", id="pagedata")["data-blob"]`. If Bandcamp restructures their HTML — which they have done historically — this returns `None` or raises a `TypeError`. The current code handles the `None` case with a `ValueError`, but a `TypeError` from `None["data-blob"]` produces a confusing traceback, not a user-friendly message.

More seriously: if Bandcamp moves the data to a different element with a different ID, the error looks identical to "invalid username" from the user's perspective because both hit the same `ValueError`.

**Why it happens:**
Unofficial API scraping has no contract. Error messages are written for the happy path and never revised when new failure modes appear.

**How to avoid:**
Add a secondary check after `soup.find()`: if `pagedata` is not None but `"data-blob"` attribute is missing, raise a distinct error ("Bandcamp page structure changed — please report this as a bug at [URL]"). Wrap `json.loads(pagedata["data-blob"])` in a `try/except (json.JSONDecodeError, KeyError, TypeError)` that gives the same "please report" message. This tells users the tool is broken, not that they typed their username wrong.

**Warning signs:**
- `json.loads(pagedata["data-blob"])` is not wrapped in exception handling (currently the case per CONCERNS.md #3)
- The `ValueError` for missing pagedata and the "structure changed" failure produce the same error message

**Phase to address:**
Error handling hardening phase (early — this is a reliability issue that exists today).

---

### Pitfall 8: Hatchling Build Excludes `bcdl.py` from Distribution

**What goes wrong:**
The entry point in `pyproject.toml` is `bcdl = "bcdl:main"`, which imports the `bcdl` module (currently `bcdl.py` at the project root). Hatchling's default include rules may or may not pick up a top-level `.py` file depending on project structure. If `bcdl.py` is not included in the built wheel, `pip install bcdl` installs a package with no importable module and the entry point crashes with `ModuleNotFoundError`.

**Why it happens:**
Hatchling by default includes packages (directories with `__init__.py`) and sometimes top-level modules. The behavior for a single-file module at root level is less obvious than for a package directory. This is never caught locally because `pip install -e .` (editable installs) always resolve from the source tree.

**How to avoid:**
Verify the built wheel before publishing: `uv build && unzip -l dist/*.whl | grep bcdl`. The wheel must contain `bcdl.py`. If not, add an explicit include in `pyproject.toml` under `[tool.hatch.build.targets.wheel]`: `include = ["bcdl.py"]`. Alternatively, convert to a package (`bcdl/__init__.py`) which Hatchling handles unambiguously.

**Warning signs:**
- Package was only ever tested with `pip install -e .` or `uv run`
- No CI step that builds, installs from wheel, and runs `bcdl --help`

**Phase to address:**
PyPI packaging phase — build verification must be part of the release checklist.

---

### Pitfall 9: Format Selection Passed Directly to yt-dlp Without Validation

**What goes wrong:**
A `--format` flag is added and passed through verbatim to yt-dlp as `["--format", args.format]`. Users pass invalid or Bandcamp-incompatible format strings (e.g., `flac` when yt-dlp uses `bestaudio[ext=flac]` syntax). yt-dlp fails mid-download with a cryptic error about format selectors. The item is marked as failed in the state file and the user must figure out yt-dlp's format syntax independently.

**Why it happens:**
Format passthrough is implemented as a convenience shortcut. The yt-dlp format string syntax is non-obvious (`bestaudio`, `bestaudio[ext=mp3]`, `251`) and differs from how users think about audio formats.

**How to avoid:**
Either (a) accept simple format names (`flac`, `mp3`, `wav`, `best`) and map them to yt-dlp format strings internally, or (b) document exactly which yt-dlp format strings work with Bandcamp and show examples in `--help`. Option (a) is better UX. If doing (a), still pass the raw string through as a fallback with a clear note that it's yt-dlp format syntax.

**Warning signs:**
- `--format` help text says "passed to yt-dlp" without examples of valid values
- No test covering how an invalid format string is reported to the user

**Phase to address:**
Format selection implementation phase.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Keying state on title instead of item ID | Easier to implement, human-readable | Re-downloads when titles change; unreliable resume | Never — use stable ID from day one |
| `subprocess.run(cmd)` with no capture | Simplest code, yt-dlp output visible | Incompatible with progress display; errors invisible programmatically | Only pre-progress-display phase |
| Blanket `except Exception` for retry | Simpler retry loop | Retries permanent failures; user waits unnecessarily | Never for retry logic |
| Writing state file non-atomically | One fewer import (`os.replace` vs plain write) | Corrupt state on kill; user loses resume progress | Never |
| Skipping wheel build verification in CI | Faster CI | Publishes broken packages silently | Never after first PyPI release |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| yt-dlp subprocess | Not checking `shutil.which("yt-dlp")` before running | Check at startup, fail fast with install instructions |
| yt-dlp subprocess | Assuming returncode=1 always means download failure | Parse stderr to distinguish "not found", "auth error", "format error", "network error" |
| Bandcamp collection API | Treating `last_token` as stable across sessions | Re-fetch from scratch on resume; tokens are session-scoped pagination cursors, not stable offsets |
| Bandcamp collection API | Not adding delay between pagination API calls | API rate limiting will trigger on large collections; apply same delay logic to pagination calls |
| PyPI / hatchling | Testing only with `pip install -e .` | Always test with a real wheel install before publishing |
| PyPI / hatchling | Publishing 0.1.0 before testing the entry point | Run `pipx install dist/*.whl && bcdl --help` as part of release process |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Accumulating all collection items before downloading | Memory grows linearly; for 2000-item collections this is ~5MB+ of dicts | For large collections, consider streaming: download each item as it is fetched | Rarely an issue under 500 items, noticeable above 2000 |
| No delay between pagination API calls | Bandcamp rate limits the pagination after ~50 rapid requests | Apply a short delay (0.5–1s) between `requests.post` pagination calls | Varies; large collections with fast pagination trigger it |
| Re-fetching entire collection on every incremental run | Slow startup for large collections | Cache or persist the last-fetched item list; use `older_than_token` to stop early once previously-seen items are reached | Collections over ~500 items |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Storing cookies file path in state file | State file checked into git exposes path (minor), but more critically: users might store state file in cloud sync directories where the cookies path becomes stale | Store only item IDs and download status in state file; never store credential paths |
| Logging full yt-dlp command (with cookies path) to stdout | Cookies file path visible in terminal logs, shell history, and CI logs | Log the command with cookies path redacted: `--cookies <redacted>` |
| Passing unsanitized user input to subprocess | Shell injection if `subprocess.run` were ever changed to `shell=True` | The current list-form call is safe; never add `shell=True` to the subprocess call |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Showing yt-dlp's full verbose output by default | Overwhelming output; users can't see overall progress | Capture yt-dlp output by default; show a single success/fail line per item; add `--verbose` flag to expose raw yt-dlp output |
| Printing "Failed items" at the end without exit code | Shell scripts / CI cannot detect failure | Exit with code 1 if any downloads failed (currently exits 0 regardless) |
| No indication that the tool is still running during API pagination | Long pause before first download starts; users think it crashed | Print "Fetching collection..." with a count as each page loads |
| State file in current working directory by default | Running from different directories creates multiple state files | Default state file location: `~/.config/bcdl/<username>.json` or `~/.local/share/bcdl/` — follow XDG base dir convention |
| `--delay` applies even after the last item | Wastes time; user thinks something is wrong | Only sleep between items, not after the last one (the code currently does this correctly on line 171 — preserve it) |

---

## "Looks Done But Isn't" Checklist

- [ ] **Resume feature:** State file records completion but does not handle the case where yt-dlp reported success (returncode=0) but the file is actually corrupt/incomplete — verify by checking if the output file exists on disk before skipping.
- [ ] **Retry logic:** Retry count is logged but yt-dlp errors are not surfaced to the user — verify that failed items show the yt-dlp error reason, not just "failed".
- [ ] **Format selection:** `--format` flag is wired to `download_item` but not verified against a real Bandcamp download — test with an actual purchased item to confirm format strings work end-to-end.
- [ ] **PyPI packaging:** `uv build` succeeds but the wheel may not include `bcdl.py` — verify with `unzip -l dist/*.whl` before publishing.
- [ ] **pipx install:** `pipx install .` installs successfully but `bcdl --help` may fail if hatchling did not include the module — test from wheel, not from source.
- [ ] **Incremental sync:** "Only download new items" requires knowing what "new" means — confirm the stop condition (e.g., first item already in state file) does not skip items added out of order.
- [ ] **Exit code:** Tool exits 0 even when downloads failed — verify `sys.exit(1)` is called when `failed` list is non-empty.

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Corrupt state file | LOW | Delete state file, re-run; all items re-download (slow but correct) |
| Wrong state file key (titles instead of IDs) | HIGH | State file is useless; must migrate or delete; all items re-download |
| PyPI name collision | MEDIUM | Rename package, re-publish; existing installs of wrong package need manual uninstall |
| Wheel missing `bcdl.py` | LOW | Fix `pyproject.toml`, re-build, re-publish new patch version |
| yt-dlp output flooding progress display | MEDIUM | Must refactor subprocess call and progress display together; interleaved concerns |
| Blanket retry on permanent errors | LOW | Fix retry predicate; no state corruption, just wasted time |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| State file corruption on kill | Resume/checkpoint phase | Test: send SIGKILL mid-write, confirm next run starts cleanly |
| State keyed on mutable title | Resume/checkpoint phase | Test: change item title in fixture, confirm it is not re-downloaded |
| yt-dlp flooding progress display | Progress display + subprocess capture phase (ship together) | Manual test: run with Rich display active, confirm no interleaved output |
| yt-dlp not in PATH | Subprocess error hardening phase | Test: mock `shutil.which` returning None, confirm clear error message |
| PyPI name collision | Packaging phase (pre-publish checklist) | Manual: `pip index versions bcdl` before building |
| Hatchling excludes `bcdl.py` | Packaging phase | CI step: build wheel, install from wheel, run `bcdl --help` |
| Retry on non-retryable errors | Retry logic phase | Test: 404 response does not trigger retry; 503 response does |
| Bandcamp DOM change confusing error | Error handling phase (early) | Test: missing `data-blob` attribute raises distinct "please report" message |
| Format string passed verbatim | Format selection phase | Test: invalid format string produces actionable error, not yt-dlp traceback |
| State file in wrong default location | Resume/checkpoint phase | Verify: running from two different directories creates one state file, not two |

---

## Sources

- Codebase inspection: `bcdl.py` (186 lines), `tests/test_bcdl.py`, `pyproject.toml` — HIGH confidence
- `.planning/codebase/CONCERNS.md` — direct technical debt inventory — HIGH confidence
- Python packaging documentation (hatchling build targets, `[project.scripts]`) — HIGH confidence, well-established behavior
- yt-dlp subprocess integration patterns — HIGH confidence, standard Python subprocess patterns
- Bandcamp API structure observed from existing code (`item_cache.collection` dict keys, `last_token` pagination) — HIGH confidence from codebase inspection
- PyPI name availability and entry point behavior — HIGH confidence, official PyPI/pip behavior
- XDG base directory convention for state files — HIGH confidence, standard on Linux/macOS

---
*Pitfalls research for: bcdl — Bandcamp Collection Downloader CLI*
*Researched: 2026-03-19*
