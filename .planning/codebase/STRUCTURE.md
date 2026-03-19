# Codebase Structure

## Directory Layout

```
bcdl/
├── bcdl.py              # Main source file — all application logic
├── pyproject.toml       # uv project config, dependencies, entry point
├── .envrc               # direnv config (auto-activates .venv)
├── README.md            # Installation and usage instructions
├── tests/
│   ├── conftest.py      # Adds project root to sys.path
│   └── test_bcdl.py     # All unit tests (mirrors bcdl.py structure)
├── .venv/               # uv-managed virtual environment (gitignored)
├── .pytest_cache/       # pytest cache (gitignored)
└── __pycache__/         # Python bytecode cache (gitignored)
```

## Key Files

| File | Purpose |
|------|---------|
| `bcdl.py` | Single-module application (186 lines). All logic: CLI, API fetching, CSV export, downloading |
| `pyproject.toml` | Project metadata, runtime deps (`requests`, `beautifulsoup4`), dev deps (`pytest`), CLI entry point |
| `tests/test_bcdl.py` | Unit tests organized into test classes per function |
| `tests/conftest.py` | Minimal — adds project root to sys.path for import |
| `.envrc` | `source .venv/bin/activate` for direnv auto-activation |

## Source Organization

`bcdl.py` is a single flat module with 4 functions + `main()`:

```
Constants (lines 21-29)
  COLLECTION_API, DEFAULT_DELAY, HEADERS

get_page_data(username) → dict       (lines 32-43)
get_all_collection_items(username) → list[dict]   (lines 46-79)
export_csv(items, path) → None       (lines 82-94)
download_item(item, index, total, cookies_file) → bool   (lines 97-117)
main() → None                        (lines 120-185)
```

## Naming Conventions

- **Files**: `snake_case.py`
- **Functions**: `snake_case`
- **Constants**: `UPPER_CASE`
- **Variables**: `snake_case`
- **Test classes**: `TestFunctionName` (maps to function being tested)
- **Test methods**: `test_describes_behavior`

## Entry Point

Configured in `pyproject.toml`:
```
[project.scripts]
bcdl = "bcdl:main"
```

Invokable as `bcdl <username>` after `uv tool install` or via `python bcdl.py <username>`.

## No Package Structure

This is a single-file script, not a package. No `__init__.py`, no submodules, no `src/` layout. The module is imported directly by name (`import bcdl`) from `conftest.py` adding the root to `sys.path`.
