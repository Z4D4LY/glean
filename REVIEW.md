# Glean — Code Review

> Date: 2026-08-01
> Scope: Full audit of the refactored codebase (post `src/` layout, tests, CI)

---

## Final Score: **B+**

Strong junior-to-mid repo. Verified: 43 tests passing, `ruff check` clean.
The candidate iterated on the prior review (`REVIEW.md` v1): flat monolith →
`src/` package, `pyproject.toml`, LICENSE, `.gitignore`, CI, pre-commit, ruff —
all present. Genuinely above average for a recruit repo.

| Dimension | Grade | Notes |
|---|---|---|
| Test coverage | B+ | 43 offline tests, good edge-case coverage; Display/ChatMode untested |
| Architecture | A- | Clean `src/` layout, DI through `BaseMode`, dataclass models |
| Code quality | B | A few real smells (`__import__`, generic Exceptions) |
| Correctness | B- | Tilde-expansion bug, "update file" duplicates instead of updating |
| Security | B+ | Key masked, `.env` gitignored, path-traversal defended + tested |
| Tooling | B | ruff/pre-commit/CI present; `ruff format` not clean, no type-checker |
| Documentation | A | README + TESTING_GUIDE are thorough |

---

## What's genuinely good

- **Architecture** — `src/` package, console entry point in `pyproject.toml`,
  dependency injection through `BaseMode.__init__` (testable), dataclass models
  using `field(default_factory=...)` correctly (no shared-mutable-default bug).
- **Testing** — 43 fully-offline tests with mocked network/LLM: parsing edge
  cases, corrupt JSON, path traversal, malformed HTML, empty body, error
  propagation. Fixtures are reused well.
- **Security hygiene** — API key masked in `ConfigMode`, `.env` gitignored,
  `StorageManager.save` sanitizes filenames via `Path(name).name` — and it's
  covered by a test.
- **Tooling** — CI matrix over Python 3.10–3.13, ruff + pre-commit configured.
- **Error handling in the mode layer** — `_scrape_and_show` wraps scrape +
  spinner cleanup in try/except.
- **Iteration on feedback** — the prior review's critical issues are all fixed.

---

## Critical Issues

### 1. `~` never expanded — `config.py:26`

```python
def get_save_dir() -> Path:
    return Path(os.getenv("SAVE_DIR", str(Path.home() / ".glean" / "scraped")))
```

The documented default in `.env.example` is `SAVE_DIR=~/.glean/scraped`.
`Path()` does **not** expand `~`, so this creates a literal `~/...` directory
relative to CWD. Verified:

```python
>>> str(Path(os.environ.get("SAVE_DIR", "~/x")))   # "~/x"
>>> str(Path(os.path.expanduser("~/x")))           # "/home/<user>/x"
```

Fix: wrap with `os.path.expanduser`.

### 2. "Update file?" duplicates instead of updating — `modes.py:69`, `modes.py:101`

```python
if self.display.confirm("Update file with summary?"):
    filepath = self.storage.save(data)  # no name → new timestamped file
```

`_summarize_and_save` and `_extract_entities_and_save` call `storage.save(data)`
without a name, so the "update" writes a **second** file rather than updating the
original. Misleading UX + silent storage bloat.

### 3. `__import__` hacks — `scraper.py:48`, `ui.py:115`

```python
scraped_at = (__import__("time").time(),)  # scraper.py:48
__import__("datetime").datetime.fromtimestamp(...)  # ui.py:115
```

Just `import time` / `from datetime import datetime`. The inline `__import__`
idiom signals the import system isn't fully understood — the biggest "recruiter
eyebrow" in the codebase.

---

## Medium Issues

| Issue | Location | Notes |
|---|---|---|
| **Fake streaming** | `client.py:29` | `stream=True` but buffers the whole response; caller prints only when done. Rename or use `rich.live`. |
| **Bare `tuple` annotation** | `scraper.py:72` | Should be `tuple[str, str]`; a type-checker would catch this. |
| **Generic `Exception` re-wrap** | `scraper.py:52`, `client.py:26` | `raise Exception(...)` erases error types; custom exceptions would be cleaner. |
| **`ruff format` not clean** | 11 files | e.g. `test_scraper.py` doubled blank lines. CI runs only pytest, so invisible until first pre-commit run. |
| **Inline `import rich`** | `modes.py:234` | Inconsistent; `rich` is already a top-level dependency. |
| **Spinner thread lifecycle** | `ui.py:38` | Daemon thread per `show_spinner`; an exception path skipping `hide_spinner` leaks threads. |
| **Re-reads `.env` per scrape** | `scraper.py:25` | `load_settings()` inside `scrape()`; should be injected once. |
| **Deps duplicated** | `requirements.txt` | Mirrors `pyproject.toml`; drift risk — pyproject should be source of truth. |

---

## Minor / Nits

- 4 entry points (`main.py`, `__main__.py`, `cli.py`, console script); `main.py`
  is legacy cruft now — README's `python main.py` only works after editable install.
- `cli.py:11` and `config.py:10` both call `load_dotenv()`.
- `__main__.py` calls `main()` at import, not under `if __name__ == "__main__":`.
- Timezone-naive timestamps (`datetime.fromtimestamp`).
- No timeout on LLM `chat()` calls.
- No `ChatMode` loop tests or `Display.print_*` rendering tests (gap also noted in the v1 review).

---

## Testing Gaps (unchanged from v1)

| What's not tested | Risk |
|---|---|
| `Display` rendering methods | Silent breakage if Rich API changes |
| Spinner thread lifecycle (double hide, hide-without-show) | Thread leak undetected |
| `ChatMode` loop (`/back`, `/exit`, empty input) | Untested edge cases |
| `_summarize_and_save` / `_extract_entities_and_save` "update" path | Duplicate-file bug undetected |
| `get_save_dir()` tilde handling | Wrong save location |

---

## Recruiter Read

**Hire signal**: tests, docs, tooling, package hygiene, and iterating on prior
feedback — all present. That's rare.

**Probe-worthy**:
1. The `__import__` hacks — does the candidate understand import semantics?
2. The duplicate-file "update" bug — suggests the manual test guide wasn't
   followed end-to-end (guide says answer `n` to the update prompt).
3. No type-checker (mypy/pyright) in the toolchain despite full type hints.

---

## Recommended Fix Order (by impact)

1. `get_save_dir()` — add `os.path.expanduser`
2. `_summarize_and_save` / `_extract_entities_and_save` — update the original file
3. Replace `__import__` hacks with proper imports
4. Run `ruff format` (or the pre-commit hook) across the repo
5. Add mypy/pyright to dev deps + CI
6. Tests for the "update file" path and `get_save_dir()`
