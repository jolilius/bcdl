# Phase 2: Download Reliability - Research

**Researched:** 2026-03-20
**Domain:** subprocess management, retry logic, yt-dlp error detection, terminal output formatting
**Confidence:** HIGH (core patterns verified via official docs and yt-dlp source/issues)

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RELY-01 | Tool retries failed requests automatically on transient failures (HTTP 429, 5xx, timeouts) without user intervention | Retry loop pattern with stderr parse; yt-dlp --retries + outer wrapper needed |
| RELY-02 | yt-dlp output captured and suppressed; only clean per-item status shown to user | subprocess.run(stdout=DEVNULL, stderr=PIPE) pattern confirmed safe |
</phase_requirements>

---

## Summary

Phase 2 has two separable but tightly coupled concerns: (1) detecting whether a yt-dlp failure is transient or permanent so the retry loop knows what to do, and (2) suppressing yt-dlp's raw terminal output and replacing it with a clean per-item status line.

The critical insight is that **yt-dlp does not distinguish transient from permanent failures by exit code alone**. All non-option failures exit with code 1. Transient detection requires parsing stderr for error string patterns. The patterns are stable and well-documented in yt-dlp's issues history: "HTTP Error 429", "HTTP Error 5" (covers 500/502/503/504), and connection/timeout strings for transient; "HTTP Error 404", "HTTP Error 401", "HTTP Error 403" for permanent. This string-based classification is the established pattern used by wrapper scripts throughout the yt-dlp ecosystem.

For output suppression, `subprocess.run(stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)` is the correct stdlib-only approach. This captures stderr for error classification while suppressing the yt-dlp download progress noise that currently reaches the terminal. `communicate()` is used internally by `subprocess.run`, eliminating deadlock risk. The pattern is safe for yt-dlp because stderr output is never large enough to exhaust the pipe buffer for a single item download.

**Primary recommendation:** Refactor `download_item` to use `subprocess.run(stdout=DEVNULL, stderr=PIPE)`, parse stderr for error class, and wrap in a retry loop using `time.sleep` with exponential backoff. No new dependencies needed.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| subprocess (stdlib) | Python 3.12 | Run yt-dlp process, capture stderr | Already used; run() + PIPE is the right pattern |
| time (stdlib) | Python 3.12 | sleep() for backoff delays | Zero-dep retry; already imported |
| random (stdlib) | Python 3.12 | Jitter for backoff | Prevents synchronized retries across items |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sys (stdlib) | Python 3.12 | Print status to stdout | Already used for output |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| stdlib retry loop | tenacity / backoff library | tenacity is excellent but adds a dependency; the retry pattern here is simple enough (3 attempts, exponential delay) that stdlib is correct |
| stderr PIPE | yt-dlp --print flag | --print only formats output fields; doesn't give access to error messages |
| string matching | yt-dlp exit code taxonomy | yt-dlp does not expose per-error-type exit codes; exit code 1 covers all non-option failures |

**Installation:**

```bash
# No new dependencies — stdlib only
```

---

## Architecture Patterns

### Recommended Project Structure

No structural changes needed. All logic lives in `bcdl.py`. The changes are:
1. Modify `download_item` signature to return richer result or keep bool + add stderr-based retry wrapper
2. Add `classify_yt_dlp_error(stderr: str) -> str` helper returning `"transient"` | `"permanent"` | `"unknown"`
3. Add `download_with_retry(item, index, total, cookies_file, max_retries, base_delay)` wrapper

### Pattern 1: subprocess with DEVNULL stdout and PIPE stderr

**What:** Run yt-dlp with stdout suppressed and stderr captured for error classification.

**When to use:** Whenever you need to silence download progress noise while still detecting error type.

**Example:**
```python
# Source: https://docs.python.org/3/library/subprocess.html
import subprocess

result = subprocess.run(
    cmd,
    stdout=subprocess.DEVNULL,   # silence yt-dlp progress/info lines
    stderr=subprocess.PIPE,       # capture for error classification
    text=True,                    # return str, not bytes
)
# result.returncode, result.stderr are now available
```

**Why DEVNULL not PIPE for stdout:** We have no use for yt-dlp's stdout (it's download progress bars and file info). Using DEVNULL avoids accumulating large buffers. Using PIPE for stdout when we don't read it is the classic deadlock scenario (official docs: "Use communicate() rather than .stdout.read() to avoid deadlocks"). `subprocess.run` with `stdout=DEVNULL` is always safe — no buffer accumulation.

### Pattern 2: Error Classification by stderr String Matching

**What:** Parse captured stderr to determine if an error is transient (retry-able) or permanent (fail-fast).

**When to use:** After any non-zero returncode from yt-dlp.

**Error string taxonomy (verified via yt-dlp issue tracker):**

```
TRANSIENT (retry with backoff):
  "HTTP Error 429"          — rate limit
  "HTTP Error 5"            — prefix matches 500/502/503/504
  "Connection reset"        — network blip
  "timed out"               — timeout
  "RemoteDisconnected"      — connection dropped mid-transfer
  "ConnectionRefused"       — transient socket error

PERMANENT (fail immediately):
  "HTTP Error 404"          — resource gone
  "HTTP Error 401"          — auth failure (cookies bad/expired)
  "HTTP Error 403"          — access denied (permanent)
  "Extractor failed"        — Bandcamp extractor error (not HTTP)
  "Unsupported URL"         — not a supported site
```

**Example:**
```python
# Source: yt-dlp issue tracker patterns + Python docs
TRANSIENT_PATTERNS = [
    "HTTP Error 429",
    "HTTP Error 5",      # 500/502/503/504
    "Connection reset",
    "timed out",
    "RemoteDisconnected",
]
PERMANENT_PATTERNS = [
    "HTTP Error 404",
    "HTTP Error 401",
    "HTTP Error 403",
    "Unsupported URL",
]

def classify_yt_dlp_error(stderr: str) -> str:
    """Returns 'transient', 'permanent', or 'unknown'."""
    for pattern in PERMANENT_PATTERNS:
        if pattern in stderr:
            return "permanent"
    for pattern in TRANSIENT_PATTERNS:
        if pattern in stderr:
            return "transient"
    return "unknown"
```

**Important:** Check permanent patterns FIRST. A 403 that arrives during a 429 scenario should be treated as permanent (403 is the authoritative failure). "Unknown" errors default to permanent to avoid infinite retry on unrecognized failures.

### Pattern 3: Exponential Backoff with Jitter (stdlib only)

**What:** After transient failure, wait with exponentially increasing delay + random jitter before retry.

**When to use:** After classifying an error as transient.

**Example:**
```python
# Source: Python docs (time.sleep) + AWS exponential backoff with jitter whitepaper pattern
import time
import random

def _backoff_delay(attempt: int, base: float = 5.0, cap: float = 60.0) -> None:
    """Sleep base * 2^attempt seconds, capped at cap, with ±25% jitter."""
    delay = min(base * (2 ** attempt), cap)
    jitter = delay * 0.25 * random.random()
    time.sleep(delay + jitter)
```

**Parameters for Bandcamp:** `base=5.0`, `cap=60.0`, `max_retries=3`. These are conservative values appropriate for a polite sequential downloader. Bandcamp's rate limits are not documented publicly but the existing `--delay` flag suggests 10s between items is already the conservative default.

### Pattern 4: Clean Per-Item Status Line

**What:** Replace raw yt-dlp output with a single status line per item.

**When to use:** Whenever `download_item` completes (success, skip, or fail).

**Output format:**
```
[skip] Artist — Title
[  1/42] Artist — Title: OK
[  2/42] Artist — Title: FAILED (HTTP Error 429 — retried 3x)
```

**Implementation:** Print the `[N/total] Artist — Title:` prefix BEFORE the subprocess call (so user sees something during the download), then print `OK` or `FAILED (reason)` on completion. Use `print(..., end="", flush=True)` for the prefix, then `print("OK")` or `print(f"FAILED ({reason})")` after.

**Example:**
```python
print(f"[{index:3}/{total}] {artist} — {title}: ", end="", flush=True)
# ... run subprocess ...
if success:
    print("OK")
else:
    print(f"FAILED ({error_reason})")
```

### Pattern 5: Summary Counts

**What:** Print downloaded / skipped / failed counts after all items processed.

**When to use:** At the end of `main()` after the download loop.

**Example:**
```python
print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {len(failed)} failed.")
```

The existing `failed` list and the `[skip]` path provide the data needed. Add `downloaded` and `skipped` counters to the loop.

### Anti-Patterns to Avoid

- **Parsing yt-dlp's progress bar output:** yt-dlp writes progress bars as ANSI escape sequences to stderr. Do not try to parse percentage/speed from these — use DEVNULL for stdout and capture only stderr for error strings.
- **Using `capture_output=True`:** This is `stdout=PIPE, stderr=PIPE`. stdout output from yt-dlp can be non-trivial for long downloads. Use `stdout=DEVNULL, stderr=PIPE` — never PIPE for stdout you won't read.
- **Reading `.stdout.read()` or `.stderr.read()` on Popen directly:** The official docs explicitly warn this causes deadlocks when pipe buffers fill. Always use `subprocess.run()` which calls `communicate()` internally, or call `communicate()` explicitly on Popen.
- **Retrying on unknown error class:** Default to permanent for unrecognized failures. Retrying unknown errors wastes user time and can worsen rate-limit situations.
- **Raising exception on yt-dlp failure:** yt-dlp exit code 1 is not exceptional — it's expected for missing/private items. Continue the loop on failure, record it, print status.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Subprocess output capture | Custom Popen + thread-based reader | `subprocess.run(stderr=PIPE)` | Deadlock-free by design; handles all edge cases |
| Retry with backoff | While-loop with manual sleep doubling | Pattern 3 above (5 lines) | The stdlib pattern is so simple it's not worth a library, but the pattern must include cap + jitter |
| yt-dlp output parsing | Regex on progress bar lines | Don't — use DEVNULL + stderr only | Progress bar uses ANSI codes, changes between yt-dlp versions |

**Key insight:** yt-dlp already has `--retries N` and `--retry-sleep` flags for fragment-level retries. These operate INSIDE the single yt-dlp invocation and apply to segment downloads. The outer wrapper retry (this phase) is DIFFERENT: it retries the entire yt-dlp invocation when it exits non-zero with a transient error. Both layers are needed and complementary.

---

## Common Pitfalls

### Pitfall 1: stdout=PIPE Without Reading Causes Deadlock

**What goes wrong:** `subprocess.run(cmd, stdout=PIPE, stderr=PIPE)` or `Popen(..., stdout=PIPE)` followed by `proc.wait()` can deadlock when stdout output exceeds the OS pipe buffer (~64KB on Linux).

**Why it happens:** yt-dlp writes download progress to stdout. If the buffer fills and bcdl isn't reading it, yt-dlp blocks. bcdl is waiting for yt-dlp to exit. Mutual deadlock.

**How to avoid:** Use `stdout=subprocess.DEVNULL` for yt-dlp stdout. We don't need it. Stderr is what we need for error classification.

**Warning signs:** Downloads hang indefinitely for large files; tests with real yt-dlp invocations hang.

### Pitfall 2: yt-dlp Writes Errors to Stderr but Progress to Both

**What goes wrong:** yt-dlp writes progress bar info to stderr (not stdout), and error messages also go to stderr. Suppressing all stderr loses error classification ability.

**Why it happens:** yt-dlp's `--quiet` flag suppresses progress but keeps error lines. Without `--quiet`, stderr contains mixed progress and error content.

**How to avoid:** Pass `--quiet` to yt-dlp (suppresses progress bars, keeps ERROR lines) and capture stderr.

**Recommended approach:**
```python
cmd = ["yt-dlp", "--quiet", "--no-progress", url]
result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
```

### Pitfall 3: Exit Code 1 Is Not Sufficient for Error Classification

**What goes wrong:** Checking only `result.returncode != 0` cannot distinguish 429 (retry) from 404 (fail fast). Both exit 1.

**Why it happens:** yt-dlp uses exit code 1 for all non-option errors (confirmed via GitHub issue #4262). Exit codes 0, 2, 100, 101 are stable and meaningful; everything else is 1.

**How to avoid:** Always parse stderr for error type on any non-zero returncode. Return code 2 (bad options) should be treated as a coding error (bug), not retried.

**Warning signs:** Code that calls `if result.returncode != 0: retry()` without classification will retry 404s forever.

### Pitfall 4: Printing Before subprocess.run Then Line Not Completing on Failure

**What goes wrong:** If you print `[1/42] Artist — Title:` with `end=""`, then the process crashes (KeyboardInterrupt, exception), the terminal shows a dangling incomplete line.

**Why it happens:** Buffered output + exception before the `print("OK")` call.

**How to avoid:** Use `flush=True` on the prefix print so it reaches the terminal immediately. Wrap the subprocess call in try/except so even on exception you print a newline.

### Pitfall 5: Retry Delay Conflicts with Existing --delay Between Items

**What goes wrong:** Retrying adds a backoff sleep, but the existing `--delay` between items also fires after the (eventual) success. This can cause much longer-than-expected pauses.

**Why it happens:** The inter-item delay logic in `main()` fires after each item regardless of how many retries happened.

**How to avoid:** The existing `time.sleep(args.delay)` fires between items and is separate from retry backoff. This is acceptable — after a retry succeeds, the regular delay still fires. Document this so future changes don't accidentally eliminate the inter-item delay.

### Pitfall 6: Existing Tests Will Break Without Mock Updates

**What goes wrong:** Current `subprocess.run` mocks return `MagicMock(returncode=0)` without setting `stderr=""`. After the refactor, code does `result.stderr` which on a MagicMock returns another MagicMock. `"HTTP Error" in MagicMock()` raises `TypeError`.

**How to avoid:** Update all `subprocess.run` mocks to include `mock_result.stderr = ""` (success) or `mock_result.stderr = "ERROR: HTTP Error 429"` (simulated failure). This is a required Wave 0 task.

---

## Code Examples

Verified patterns from official sources and yt-dlp issue tracker:

### subprocess with DEVNULL stdout + PIPE stderr

```python
# Source: https://docs.python.org/3/library/subprocess.html
import subprocess

def _run_yt_dlp(cmd: list[str]) -> tuple[int, str]:
    """Run yt-dlp, suppress stdout, capture stderr. Returns (returncode, stderr)."""
    result = subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.returncode, result.stderr
```

### Full retry wrapper for download_item

```python
# Source: stdlib patterns + yt-dlp exit code documentation (github.com/yt-dlp/yt-dlp/issues/4262)
import time
import random

TRANSIENT_PATTERNS = ["HTTP Error 429", "HTTP Error 5", "Connection reset", "timed out", "RemoteDisconnected"]
PERMANENT_PATTERNS = ["HTTP Error 404", "HTTP Error 401", "HTTP Error 403", "Unsupported URL", "Extractor failed"]

def classify_yt_dlp_error(stderr: str) -> str:
    for pat in PERMANENT_PATTERNS:
        if pat in stderr:
            return "permanent"
    for pat in TRANSIENT_PATTERNS:
        if pat in stderr:
            return "transient"
    return "unknown"

def download_with_retry(
    item: dict,
    index: int,
    total: int,
    cookies_file: str | None = None,
    max_retries: int = 3,
    base_delay: float = 5.0,
) -> tuple[bool, str]:
    """
    Returns (success, error_reason).
    error_reason is "" on success, human-readable string on failure.
    """
    url = item.get("item_url") or item.get("tralbum_url")
    artist = item.get("band_name") or "Unknown Artist"
    title = item.get("album_title") or item.get("item_title") or "Unknown"

    if not url:
        return False, "no URL"

    cmd = ["yt-dlp", "--quiet", "--no-progress", url]
    if cookies_file:
        cmd += ["--cookies", cookies_file]

    print(f"[{index:3}/{total}] {artist} \u2014 {title}: ", end="", flush=True)

    for attempt in range(max_retries + 1):
        returncode, stderr = _run_yt_dlp(cmd)

        if returncode == 0:
            print("OK")
            return True, ""

        error_class = classify_yt_dlp_error(stderr)

        if error_class in ("permanent", "unknown"):
            reason = _extract_error_summary(stderr)
            print(f"FAILED ({reason})")
            return False, reason

        # transient — retry with backoff
        if attempt < max_retries:
            delay = min(base_delay * (2 ** attempt), 60.0)
            delay += delay * 0.25 * random.random()
            print(f"\n  [retry {attempt + 1}/{max_retries}] waiting {delay:.0f}s\u2026", end="", flush=True)
            time.sleep(delay)
        else:
            reason = _extract_error_summary(stderr)
            print(f"FAILED (retried {max_retries}x: {reason})")
            return False, reason

    return False, "max retries exceeded"  # unreachable but satisfies type checker


def _extract_error_summary(stderr: str) -> str:
    """Extract first ERROR: line from stderr for display."""
    for line in stderr.splitlines():
        if line.startswith("ERROR:"):
            return line[7:].strip()[:80]  # truncate for terminal
    return "unknown error"
```

### Updated summary in main()

```python
# Replace the existing final print with:
downloaded = len(items) - len(failed) - skipped
print(f"\nDone: {downloaded} downloaded, {skipped} skipped, {len(failed)} failed.")
if failed:
    print("Failed items:")
    for item in failed:
        title = item.get("album_title") or item.get("item_title") or "Unknown"
        artist = item.get("band_name") or "Unknown Artist"
        print(f"  - {artist} \u2014 {title}")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| subprocess.run(cmd) — inherits terminal | subprocess.run(stdout=DEVNULL, stderr=PIPE) | Python 3.5+ (DEVNULL added) | Clean separation of yt-dlp noise from bcdl status |
| Retry libraries (tenacity) | stdlib loop with time.sleep + random.uniform | Always available | No new dependency for simple sequential retry |
| Exit code as error signal | stderr string matching | Always been the case for yt-dlp | Necessary; yt-dlp will not add per-type exit codes soon |

**Deprecated/outdated:**
- `subprocess.PIPE` for stdout when you don't need stdout content: replaced by `subprocess.DEVNULL` (Python 3.3+)
- `proc.stdout.read()` manual reading: replaced by `communicate()` / `subprocess.run()` to avoid deadlocks

---

## Open Questions

1. **yt-dlp --quiet behavior on Bandcamp specifically**
   - What we know: `--quiet` suppresses progress bars and keeps ERROR/WARNING lines in stderr (verified for YouTube; yt-dlp behavior is consistent across extractors)
   - What's unclear: Whether Bandcamp extractor writes any useful diagnostic to stdout that would be lost with DEVNULL
   - Recommendation: Test with a real Bandcamp URL in Phase 2 execution; the implementation is safe to ship since the current code already shows no Bandcamp-specific stdout

2. **Bandcamp's actual rate limit behavior**
   - What we know: The project already uses a 10s default delay between items. Bandcamp is known to rate-limit aggressively.
   - What's unclear: Exact HTTP 429 Retry-After header usage by Bandcamp — does it send one?
   - Recommendation: Ignore Retry-After for Phase 2. Our backoff (5s/10s/20s) is conservative. Retry-After parsing can be added in a future phase if needed.

3. **Test strategy for retry behavior**
   - What we know: Existing tests mock `subprocess.run`; retry logic can be tested the same way
   - Recommendation: Tests should assert the exact status line format to prevent regression (STATE.md locked: output capture and display ship together)

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x |
| Config file | none (pytest auto-discovers tests/) |
| Quick run command | `python -m pytest tests/test_bcdl.py -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Test Class |
|--------|----------|-----------|-----------|
| RELY-01 | Transient error (429/5xx) triggers retry with backoff | unit | `TestRetryLogic` |
| RELY-01 | Permanent error (404/401/403) fails immediately, no retry | unit | `TestRetryLogic` |
| RELY-01 | Max retries exceeded → item marked failed | unit | `TestRetryLogic` |
| RELY-02 | yt-dlp stdout not reaching terminal (DEVNULL) | unit | `TestDownloadOutput` |
| RELY-02 | Single status line per item (not raw yt-dlp output) | unit | `TestDownloadOutput` |
| RELY-02 | Final summary shows downloaded/skipped/failed counts | unit | `TestMainSummary` |

### Wave 0 Gaps (existing tests need mock updates)

- [ ] All `subprocess.run` mocks need `mock_result.stderr = ""` added — currently missing, will `TypeError` after refactor
- [ ] Add `TestRetryLogic` class — covers RELY-01 retry/permanent/transient/max-retries cases
- [ ] Add `TestDownloadOutput` class — covers RELY-02 output suppression and status line format
- [ ] Add `TestMainSummary` — covers final summary counts
- [ ] Add `TestClassifyYtdlpError` — unit tests for each pattern category in classify_yt_dlp_error

*(No new test files needed — add classes to existing `tests/test_bcdl.py`)*

---

## Sources

### Primary (HIGH confidence)

- https://docs.python.org/3/library/subprocess.html — DEVNULL, PIPE, communicate() deadlock warning, subprocess.run API
- https://github.com/yt-dlp/yt-dlp/issues/4262 — yt-dlp exit code taxonomy (0, 1, 2, 100, 101)
- https://man.archlinux.org/man/extra/yt-dlp/yt-dlp.1.en — --quiet, --no-progress, --retries, --retry-sleep flags

### Secondary (MEDIUM confidence)

- https://github.com/yt-dlp/yt-dlp/issues/9427 — HTTP 429 treated as extraction failure (not retried by default within extractor)
- GitHub issues #8005, #14145, #14680 — confirmed stderr error string formats for 404/403

### Tertiary (LOW confidence — verify during implementation)

- https://github.com/yt-dlp/yt-dlp/issues/13729 — Bandcamp extractor "Extractor failed to obtain id" error (geographically inconsistent, may not affect all users)

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stdlib only; subprocess docs verified
- Architecture: HIGH — subprocess DEVNULL/PIPE pattern from official docs; exit code taxonomy from yt-dlp official issue
- Pitfalls: HIGH — deadlock warning is explicit in official Python docs; exit code 1 ambiguity confirmed in yt-dlp issue tracker
- Error string patterns: MEDIUM — confirmed for YouTube and generic cases via issue tracker; Bandcamp-specific strings should be validated during implementation

**Research date:** 2026-03-20
**Valid until:** 2026-06-20 (stdlib patterns are stable; yt-dlp exit codes marked as stable by maintainers)
