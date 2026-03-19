# Phase 1: State Foundation - Research

**Researched:** 2026-03-19
**Domain:** Python stdlib patterns for atomic file writes, subprocess detection, state management in a single-file CLI
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**State file format**
- Location: `.bcdl/{username}.json`
- Key: `sale_item_id` as a string (stable numeric ID from Bandcamp API, tied to the purchase record)
- Value: minimal metadata object — `{ "artist": "...", "title": "...", "url": "...", "downloaded_at": "..." }`
- Example entry: `{ "12345678": { "artist": "Burial", "title": "Untrue", "url": "https://...", "downloaded_at": "2026-03-19T14:23:00" } }`

**State write timing**
- Write to state after successful download only (yt-dlp exit code 0)
- Failed items are NOT recorded — they will be retried on the next run
- Corrupt/partial state from Ctrl-C must not happen — use atomic write (write to temp file, then rename)

**Skip output**
- One line per skipped item: `[skip] Artist — Title`
- Visually distinct from download lines (which use `[N/M] Artist — Title` format)
- No change to the existing download line format

**yt-dlp detection**
- Check at startup, before fetching the collection — fail fast, no wasted network calls
- Error message (exact): `Error: yt-dlp is not installed. Install it with: pip install yt-dlp`
- Exit with non-zero code after printing this message

### Claude's Discretion

- Atomic write implementation (write-then-rename pattern using `tempfile` + `os.replace`)
- Whether StateManager is a class or a set of functions
- Where StateManager lives (same file or new module) — keep it simple for a 186-line codebase
- Exact `downloaded_at` timestamp format (ISO 8601 recommended)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| RESM-01 | Tool tracks downloaded items in a local state file so already-downloaded items are skipped on subsequent runs | Atomic write pattern (os.replace), state keyed by sale_item_id, skip logic in download loop |
</phase_requirements>

---

## Summary

Phase 1 is a pure Python stdlib implementation — no new dependencies are required. All needed capabilities (`json`, `os`, `tempfile`, `shutil`, `datetime`) are present in Python 3.12's standard library. The four behaviors being added (yt-dlp detection, state file creation, atomic write, skip-on-rerun) each map to a small, focused code change in `main()` and a new StateManager abstraction.

The highest-risk decision already made is the state key: `sale_item_id`. The existing `get_all_collection_items()` function discards the item dict keys when it calls `list(...values())`, so `sale_item_id` must be accessed as a field within each item's dict (via `item.get("sale_item_id")`). If an item is missing this field, it cannot be tracked and should be treated as a download-but-never-skip item (same as current behavior for items without a URL). This edge case must be handled explicitly.

The atomic write pattern is well-understood on POSIX: write JSON to a `.tmp` file in the same directory as the target (critical — same filesystem guarantees `os.replace()` atomicity), then call `os.replace()`. A partial write followed by a kill leaves the `.tmp` file behind, not a truncated target. The `.tmp` file should be cleaned up on the next successful write.

**Primary recommendation:** Keep StateManager as module-level functions in `bcdl.py` (not a class, not a new module). The codebase is 186 lines; a class or new file would be over-engineered. The functions needed are: `load_state(path) -> dict`, `save_state(state, path) -> None`, and the in-loop check `is_downloaded(state, item_id) -> bool`.

---

## Standard Stack

### Core (no new dependencies required for this phase)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `json` (stdlib) | Python 3.12 built-in | State file serialization | Human-readable, zero deps, adequate for flat key-value state |
| `os` (stdlib) | Python 3.12 built-in | `os.replace()` for atomic rename | POSIX-atomic: rename is guaranteed atomic on the same filesystem |
| `tempfile` (stdlib) | Python 3.12 built-in | `NamedTemporaryFile` for safe temp writes | Creates tmp in same dir (same filesystem), handles naming |
| `shutil` (stdlib) | Python 3.12 built-in | `shutil.which()` for yt-dlp detection | Checks PATH without spawning a subprocess |
| `datetime` (stdlib) | Python 3.12 built-in | ISO 8601 timestamps for `downloaded_at` | `datetime.now(timezone.utc).isoformat(timespec='seconds')` |
| `pathlib` (stdlib) | Python 3.12 built-in | `.bcdl/` dir creation | `Path.mkdir(parents=True, exist_ok=True)` |

**Installation:** No new packages. This phase adds zero production dependencies.

**Version verification:** All stdlib — no version pinning needed.

### Supporting (test tooling — already installed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest` | already in dev deps | Test runner | `uv run pytest` |
| `unittest.mock` | stdlib | Patching `shutil.which`, `subprocess.run`, `os.replace` | Existing pattern in test_bcdl.py |

---

## Architecture Patterns

### Recommended Structure

No new files. All changes stay in `bcdl.py`. The state management code is ~40 lines — a new module would be premature for a 186-line codebase.

```
bcdl.py                    # All production code (current + new)
  load_state(path)         # New: reads .bcdl/{username}.json, returns {} on missing/corrupt
  save_state(state, path)  # New: atomic write via NamedTemporaryFile + os.replace
  main()                   # Modified: yt-dlp check, state init, skip check, state write

tests/
  test_bcdl.py             # Existing tests + new tests for state logic
```

### Pattern 1: Fail-Fast yt-dlp Detection

**What:** Call `shutil.which("yt-dlp")` at the top of `main()`, before any network calls. If None, print the exact error message and `sys.exit(1)`.

**When to use:** Always — first thing in `main()` after `args = parser.parse_args()`.

**Why `shutil.which` over `subprocess.run(["yt-dlp", "--version"])`:** No subprocess overhead, no side effects, faster. Use `subprocess` only if you need to enforce a minimum version constraint (not required here).

**Example:**
```python
# Source: Python docs — shutil.which, sys.exit pattern matches existing error handling in main()
import shutil

def main() -> None:
    args = parser.parse_args()

    if shutil.which("yt-dlp") is None:
        print("Error: yt-dlp is not installed. Install it with: pip install yt-dlp",
              file=sys.stderr)
        sys.exit(1)
    # ... rest of main
```

### Pattern 2: Atomic State Write

**What:** Write JSON to a `.tmp` file in the same directory as the target, then call `os.replace()`. The temp file must be in the same directory (same filesystem) to guarantee `os.replace()` is atomic on POSIX.

**When to use:** Every time state is updated (after each successful download).

**Example:**
```python
# Source: Python docs — os.replace, tempfile.NamedTemporaryFile
import os
import json
import tempfile
from pathlib import Path

def save_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tf:
        json.dump(state, tf, indent=2)
        tmp_path = tf.name
    os.replace(tmp_path, path)
```

**Critical constraint:** `dir=path.parent` — temp file must be on the same filesystem as the target. Do NOT use the default `/tmp` directory, which may be a different filesystem than the `.bcdl/` directory.

### Pattern 3: Resilient State Load

**What:** Load the state file, returning an empty dict on any failure (missing file, corrupt JSON, permission error). Log a warning on corrupt state (don't silently swallow it), but do not crash.

**When to use:** Once at startup, before the download loop.

**Example:**
```python
# Source: Python docs — json.JSONDecodeError, pathlib
def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: state file unreadable ({e}), starting fresh", file=sys.stderr)
        return {}
```

### Pattern 4: Skip Check and State Write in Download Loop

**What:** Before calling `download_item()`, check if `str(item.get("sale_item_id"))` is a key in the loaded state. After a successful download, update the state dict and call `save_state()`.

**When to use:** The download loop in `main()`.

**Example:**
```python
# Source: derived from existing loop pattern in bcdl.py:165-173
state_path = Path(".bcdl") / f"{args.username}.json"
state = load_state(state_path)

for i, item in enumerate(items, 1):
    item_id = str(item.get("sale_item_id", ""))
    artist = item.get("band_name") or "Unknown Artist"
    title = item.get("album_title") or item.get("item_title") or "Unknown"

    if item_id and item_id in state:
        print(f"[skip] {artist} — {title}")
        continue

    success = download_item(item, i, len(items), cookies_file=args.cookies)
    if success and item_id:
        state[item_id] = {
            "artist": artist,
            "title": title,
            "url": item.get("item_url") or item.get("tralbum_url") or "",
            "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        save_state(state, state_path)
```

### Anti-Patterns to Avoid

- **Temp file in `/tmp`:** `os.replace("/tmp/bcdl.tmp", ".bcdl/user.json")` may cross filesystems and fail on some systems. Always use `dir=path.parent`.
- **Accumulate-then-write:** Writing state only at the end of the run means a Ctrl-C after 50/100 downloads loses all 50. Write after each successful download.
- **Silent corrupt state:** Catching `json.JSONDecodeError` and returning `{}` without printing a warning means users run from scratch with no explanation.
- **State write before returncode check:** Writing to state when `result.returncode != 0` would permanently skip items that failed to download. Only write on `returncode == 0`.
- **Keying on title:** Already locked against by decision — but the implementation must not accidentally use `artist + title` as a fallback key when `sale_item_id` is missing. Missing ID = no state entry (download runs every time, same as today).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Atomic file rename | Custom lock file / write-and-swap logic | `os.replace()` | POSIX-guaranteed atomic on same filesystem; one stdlib call |
| Temp file naming | Manual `.tmp` suffix construction | `tempfile.NamedTemporaryFile(dir=..., delete=False)` | Handles naming, collision avoidance, cleanup |
| Binary PATH search | Walking `os.environ["PATH"]` manually | `shutil.which()` | Handles PATH splitting, permission bits, platform differences |
| ISO timestamp | Manual string formatting | `datetime.now(timezone.utc).isoformat(timespec="seconds")` | Correct UTC offset, no timezone bugs |

**Key insight:** Every problem in this phase has a one-line stdlib solution. The risk is not missing a library — it's using the library incorrectly (wrong `dir` arg to `NamedTemporaryFile`, using local time instead of UTC for timestamps).

---

## Common Pitfalls

### Pitfall 1: Temp File on a Different Filesystem

**What goes wrong:** `os.replace(src, dst)` raises `OSError: [Errno 18] Invalid cross-device link` when `src` and `dst` are on different filesystems (e.g., `/tmp` vs a mounted home directory). This is a silent test gap because macOS and most Linux CI setups have `/tmp` and `~` on the same device, but Docker containers and network mounts do not.

**Why it happens:** Developers use `tempfile.NamedTemporaryFile()` without specifying `dir=`, which defaults to `/tmp`.

**How to avoid:** Always pass `dir=path.parent` to `NamedTemporaryFile`. Verified working in test above.

**Warning signs:** Atomic write test only covers the happy path on the developer's machine.

### Pitfall 2: Missing `sale_item_id` Field in Item Dict

**What goes wrong:** `get_all_collection_items()` returns items as list values; the dict keys (which were numeric IDs in `item_cache.collection`) are discarded. If `sale_item_id` is absent from the item object (e.g., for tracks vs albums, or for items fetched via pagination API), `item.get("sale_item_id")` returns `None`, the state entry is keyed as `"None"`, and all such items are permanently skipped after the first run.

**Why it happens:** The field name `sale_item_id` was chosen based on the Bandcamp API contract, but its presence was not verified in the existing test fixtures (which don't include this field in `ITEM_A`, `ITEM_B`).

**How to avoid:** Guard the state key: `item_id = str(item.get("sale_item_id", ""))`. If `item_id` is empty string, skip writing to state and skip the skip-check. The item behaves as if state tracking is disabled for it. Add test fixtures that include `sale_item_id` to verify the happy path, and fixtures without it to verify the fallback.

**Warning signs:** Test fixtures don't include `sale_item_id`.

### Pitfall 3: State Written After Loop vs After Each Item

**What goes wrong:** A developer puts `save_state()` after the `for` loop instead of inside it. A Ctrl-C at item 50/100 means the state file is never written, and all 50 successful downloads are lost from the state. The next run re-downloads all 50.

**Why it happens:** "Write at the end" is the natural pattern for file output; incrementally updating state requires a mental shift to "write on each success."

**How to avoid:** Place `save_state()` immediately after the state dict update inside the `if success and item_id:` block. Test by simulating a run that downloads 2 items and verifying the state file after each one.

**Warning signs:** `save_state()` call is outside the `for` loop.

### Pitfall 4: yt-dlp Check Placed After Network Calls

**What goes wrong:** If the yt-dlp check is placed after `get_all_collection_items()`, the tool fetches the entire Bandcamp collection (potentially multiple paginated API calls) before failing with "yt-dlp not installed." The user waits 5-30 seconds before seeing the error.

**Why it happens:** It feels natural to check yt-dlp "just before" the first download.

**How to avoid:** The check must be the first action in `main()` after argument parsing, before any network calls. The CONTEXT.md decision explicitly says "before fetching the collection."

### Pitfall 5: Printing Skip Message for Items Without `sale_item_id`

**What goes wrong:** An item missing `sale_item_id` would never match the state and would never print `[skip]`. This is correct behavior — it should download every time. But if the guard isn't explicit, a future developer may add `"None" in state` as a "fix," accidentally locking out all such items.

**How to avoid:** The `if item_id and item_id in state:` guard makes intent explicit — empty item_id is treated as "always download."

---

## Code Examples

Verified patterns from Python 3.12 stdlib:

### Atomic Write (verified working on macOS, same filesystem)
```python
# Source: Python docs — os.replace (POSIX atomic), tempfile.NamedTemporaryFile
import os, json, tempfile
from pathlib import Path

def save_state(state: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, suffix=".tmp", encoding="utf-8"
    ) as tf:
        json.dump(state, tf, indent=2)
        tmp_path = tf.name
    os.replace(tmp_path, path)
```

### Resilient State Load
```python
# Source: Python docs — json.JSONDecodeError
def load_state(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: state file unreadable ({e}), starting fresh", file=sys.stderr)
        return {}
```

### yt-dlp Detection (verified: shutil.which returns None when not installed)
```python
# Source: Python docs — shutil.which, follows existing sys.exit(1) pattern in main()
import shutil, sys

if shutil.which("yt-dlp") is None:
    print("Error: yt-dlp is not installed. Install it with: pip install yt-dlp",
          file=sys.stderr)
    sys.exit(1)
```

### ISO 8601 UTC Timestamp (verified output: "2026-03-19T12:20:45+00:00")
```python
# Source: Python docs — datetime.isoformat(timespec)
from datetime import datetime, timezone

downloaded_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
# → "2026-03-19T12:20:45+00:00"
```

### Directory Creation
```python
# Source: Python docs — Path.mkdir
from pathlib import Path

state_path = Path(".bcdl") / f"{username}.json"
state_path.parent.mkdir(parents=True, exist_ok=True)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `open(path, "w")` then `json.dump()` | `NamedTemporaryFile + os.replace()` | Python 3.3+ (os.replace added) | Write is atomic: Ctrl-C leaves old file intact, not truncated |
| `subprocess.run(["yt-dlp", "--version"])` for detection | `shutil.which("yt-dlp")` | N/A (shutil.which existed since 2.x) | No subprocess spawn, no side effects, faster |
| No state tracking (current bcdl.py) | JSON state keyed by stable numeric ID | This phase | Downloads resume correctly; no re-downloads on rerun |

**Deprecated/outdated:**
- `os.rename()` instead of `os.replace()`: On Windows, `os.rename()` raises if destination exists; `os.replace()` overwrites atomically. Always use `os.replace()`.
- `shelve` for state: Platform-dependent backend (ndbm/gdbm/dumbdbm). Not portable. Not human-readable. Avoid.

---

## Open Questions

1. **Is `sale_item_id` always present in Bandcamp API item dicts?**
   - What we know: CONTEXT.md locked it as the state key. The existing test fixtures (`ITEM_A`, `ITEM_B`) don't include this field, so it hasn't been exercised.
   - What's unclear: Whether the API returns `sale_item_id` for all items, or only for purchase-record items (not free downloads, etc.).
   - Recommendation: Guard with `item.get("sale_item_id", "")` and treat missing as "no state tracking for this item." Update test fixtures to include `sale_item_id` for items that should be tracked.

2. **Should the state file path be computed relative to CWD or absolute?**
   - What we know: CONTEXT.md says `.bcdl/{username}.json` (relative). The UX pitfalls research flagged "running from different directories creates multiple state files" as a known issue (flagged for future phases, not this one).
   - What's unclear: Nothing — this is already decided as relative, matching the locked decision. XDG-compliance is out of scope for Phase 1 per requirements.
   - Recommendation: Use `Path(".bcdl") / f"{args.username}.json"` (relative to CWD). This is correct for Phase 1. Phase 3 can move to `~/.local/share/bcdl/` if needed.

---

## Validation Architecture

> nyquist_validation is enabled in .planning/config.json.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already installed in dev deps) |
| Config file | none — discovered via conftest.py |
| Quick run command | `uv run pytest tests/test_bcdl.py -x -q` |
| Full suite command | `uv run pytest -q` |

**Baseline:** 14 tests, all passing. Phase 1 adds new tests; must not break existing 14.

### Phase Requirements → Test Map

| Req ID | Success Criterion | Test Type | Automated Command | File Exists? |
|--------|-------------------|-----------|-------------------|-------------|
| RESM-01 / SC-1 | yt-dlp not installed → clear error, not traceback | unit | `uv run pytest tests/test_bcdl.py -k "test_ytdlp_not_installed" -x` | Wave 0 |
| RESM-01 / SC-2 | State file created after successful run, keyed by sale_item_id | unit | `uv run pytest tests/test_bcdl.py -k "test_state_written_after_download" -x` | Wave 0 |
| RESM-01 / SC-3 | State file survives Ctrl-C (atomic write) | unit | `uv run pytest tests/test_bcdl.py -k "test_atomic_write" -x` | Wave 0 |
| RESM-01 / SC-4 | Second run skips already-downloaded items, prints `[skip]` | unit | `uv run pytest tests/test_bcdl.py -k "test_skip_already_downloaded" -x` | Wave 0 |

### Detailed Test Scenarios

**SC-1: yt-dlp not installed**
```python
# Patch shutil.which to return None, call main() with sys.argv set, assert sys.exit(1)
# Assert stderr contains exact message: "Error: yt-dlp is not installed. Install it with: pip install yt-dlp"
with patch("shutil.which", return_value=None):
    with patch("sys.argv", ["bcdl", "testuser"]):
        with pytest.raises(SystemExit) as exc:
            bcdl.main()
assert exc.value.code == 1
```

**SC-2 and SC-4: State file created + skip on rerun**
```python
# Use tmp_path fixture, patch download_item to return True (success),
# patch get_all_collection_items to return items with sale_item_id,
# verify state file exists and contains correct keys
# On second call with same state, verify download_item is NOT called (skip path taken)
# Verify "[skip] Artist — Title" is printed
```

**SC-3: Atomic write (Ctrl-C safety)**
```python
# Verify save_state uses NamedTemporaryFile + os.replace, not plain open()
# Test: if os.replace raises (simulated), the tmp file exists but target is intact
# Test: after successful save_state, no .tmp files remain
# Verify: load_state after os.replace sees the new data
```

**load_state resilience (supporting tests)**
```python
# Test: missing state file → returns {}
# Test: corrupt JSON in state file → returns {}, prints warning to stderr
# Test: valid state file → returns dict with correct keys
```

### Sampling Rate

- **Per task commit:** `uv run pytest -x -q` (full suite, fast — 14 + ~8 new tests, ~0.5s)
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] New test cases for `load_state`, `save_state`, yt-dlp detection, and skip logic — these do not exist yet and must be added before or alongside implementation

*(No new test infrastructure needed — pytest, conftest.py, and mock patterns are all in place)*

---

## Sources

### Primary (HIGH confidence)

- Python 3.12 stdlib docs — `os.replace`, `tempfile.NamedTemporaryFile`, `shutil.which`, `datetime.isoformat` — verified by running locally
- `/Users/jolilius/home/src/bcdl/bcdl.py` — existing implementation, entry points, current patterns
- `/Users/jolilius/home/src/bcdl/tests/test_bcdl.py` — existing test patterns (patch, pytest, MagicMock)
- `/Users/jolilius/home/src/bcdl/.planning/phases/01-state-foundation/01-CONTEXT.md` — locked decisions
- `/Users/jolilius/home/src/bcdl/.planning/research/PITFALLS.md` — project-level pitfalls research (HIGH confidence, codebase-derived)
- `/Users/jolilius/home/src/bcdl/.planning/research/STACK.md` — project-level stack research

### Secondary (MEDIUM confidence)

- CONTEXT.md assertion that `sale_item_id` is the correct Bandcamp API field name — trusted as a locked decision; not independently verified against live API

### Tertiary (LOW confidence)

- None — this phase uses only stdlib and existing patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all stdlib, no new dependencies, verified locally
- Architecture: HIGH — derived from existing 186-line codebase; keeping everything in one file is unambiguous
- Pitfalls: HIGH — each pitfall was verified with a local test or traces directly to existing code
- `sale_item_id` field: MEDIUM — locked by user decision; not independently verified against live Bandcamp API

**Research date:** 2026-03-19
**Valid until:** 2026-06-19 (90 days — stdlib patterns are stable; only risk is Bandcamp changing their API field names)
