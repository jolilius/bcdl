# Technology Stack

**Analysis Date:** 2026-03-19

## Languages

**Primary:**
- Python 3.12+ - All application code, CLI tool

## Runtime

**Environment:**
- Python 3.12 or higher (specified in `pyproject.toml`)

**Package Manager:**
- uv - Package manager and project manager
- Lockfile: `uv.lock` (present, pinned dependencies)

## Frameworks

**Core:**
- Click/Argparse - CLI argument parsing (built-in `argparse` used in `bcdl.py`)

**Testing:**
- pytest - Unit testing framework
  - Config: Implicit (no separate config file, uses defaults)
  - Version: Managed via `uv.lock`

**Build/Dev:**
- hatchling - Build backend for packaging
- direnv - Development environment activation (`.envrc` present)

## Key Dependencies

**Critical:**
- requests 2.x.x - HTTP client for Bandcamp API calls
  - Used in: `bcdl.py` for fetching user collection pages and paginating via API
  - Purpose: GET/POST requests to Bandcamp endpoints

- beautifulsoup4 4.14.3 - HTML parsing library
  - Used in: `bcdl.py` for extracting JSON data-blob from Bandcamp HTML pages
  - Purpose: Parse `<div id="pagedata">` and extract embedded JSON

**Infrastructure:**
- certifi 2026.2.25 - SSL certificate verification
- charset-normalizer 3.4.6 - Character encoding detection for HTTP
- idna 3.11 - Internationalized domain name support
- urllib3 (via requests) - HTTP library underlying requests

**Dev/Test:**
- pytest - Test execution framework
- soupsieve - CSS selector library (dependency of beautifulsoup4)
- typing-extensions - Type hint support

## Configuration

**Environment:**
- No required environment variables for operation
- Project uses user-provided Bandcamp username as CLI argument
- Optional: `--cookies` file path for authenticated access to purchased items

**Build:**
- `pyproject.toml` - Project metadata and dependencies
- `uv.lock` - Locked dependency versions for reproducible builds

## Platform Requirements

**Development:**
- Python 3.12+
- uv package manager
- yt-dlp (external tool, installed via Homebrew, not in Python dependencies)

**Production:**
- Python 3.12+
- yt-dlp (external tool for actual download functionality)
- No specific deployment platform; runs as CLI tool on any platform with Python 3.12+

---

*Stack analysis: 2026-03-19*
