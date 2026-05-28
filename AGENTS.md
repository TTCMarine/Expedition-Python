# Agent and contributor guide

This file helps AI assistants (Cursor, etc.) and contributors work effectively on **Expedition-Python**.

## What this project is

A Python **ctypes** wrapper around Expedition’s `ExpDLL.dll` for sailing navigation integration on Windows.

| Area | Location |
|------|----------|
| DLL wrapper | [`Expedition/dll_wrapper.py`](Expedition/dll_wrapper.py) |
| Channel / system enums | [`Expedition/enums.py`](Expedition/enums.py) |
| Package version | [`Expedition/version.py`](Expedition/version.py) (dynamic in [`pyproject.toml`](pyproject.toml)) |
| Tests | [`tests/test_expedition.py`](tests/test_expedition.py) |
| User docs (Sphinx) | [`docs/`](docs/), built via [`readthedocs.yaml`](readthedocs.yaml) |

Runtime: **Windows only** for real DLL use. CI runs on Linux/macOS/Windows; integration tests **skip** when `ExpDLL.dll` is unavailable.

## Reference headers (local dev, not in git)

Expedition’s C headers are proprietary. Sync them locally for binding work and enum maintenance:

```bash
uv run python scripts/sync_expedition_headers.py
uv run python scripts/check_enums_against_headers.py
```

- Headers live under `reference/expedition/` (gitignored). See [`reference/README.md`](reference/README.md).
- **Do not commit** headers or bundle them in the wheel.
- `CoreMem.h` is not shipped with Expedition; channel layout comes from `user_channels.h` / `sys_channels.h`.
- After an Expedition upgrade: sync headers → `generate_enums_from_headers.py --write` → check-enums → update `dll_wrapper.py` if `ExpDLL.h` changed → run tests.

### Enum naming (2.0+)

Python enum members use **mechanical** names from the C headers (no override tables):

| C enum | Strip prefix | Example |
|--------|--------------|---------|
| `ExChannels` | `Ex` | `ExLwy` → `Lwy` |
| `ExSysChannels` | `ExSys` (or `Ex` for `ExNumSysChannels`) | `ExSysMouseTime` → `MouseTime` |
| `ExSysBooleanChannels` | `ExSysBool` | `ExSysBoolAutoPan` → `AutoPan` |
| `ExSysIntChannels` | `ExSysInt` | `ExSysIntTheme` → `Theme` |

Regenerate [`Expedition/enums.py`](Expedition/enums.py) from synced headers:

```bash
uv run python scripts/generate_enums_from_headers.py --write
```

Shared parsing lives in [`scripts/_header_enums.py`](scripts/_header_enums.py).

## uv workflow

[uv](https://docs.astral.sh/uv/) is the recommended dev tool (see `.python-version` for local Python, typically 3.12; package supports 3.8+).

```bash
uv sync
uv run python scripts/sync_expedition_headers.py      # Windows: refresh reference headers
uv run python scripts/generate_enums_from_headers.py --write
uv run python scripts/check_enums_against_headers.py
uv run pytest tests/ -v
uv run black . && uv run isort .
uv run ruff check .
uv build
```

Install for end users: `pip install Expedition-Python` (PyPI). Editable dev install: `uv sync` or `pip install -e .`.

## GitHub Actions

| Workflow | Trigger | Role |
|----------|---------|------|
| [`.github/workflows/test.yml`](.github/workflows/test.yml) | push/PR to `main`, releases | Matrix: Ubuntu, macOS, Windows × Python 3.8–12. `uv sync`, `uv build`, install wheel, `pytest`. Real DLL tests only when Expedition is present on Windows. |
| Same file, `lint` job | push/PR to `main` | `black --check`, `isort --check`, `ruff check`, `mypy` (mypy may fail without blocking). |
| [`.github/workflows/version.yml`](.github/workflows/version.yml) | push to `main` | Auto-increment patch in `version.py`, commit, tag `vX.Y.Z`, push. |
| [`.github/workflows/publish.yml`](.github/workflows/publish.yml) | GitHub release **published** | Run tests, `uv build`, publish to PyPI (trusted publishing). |

Releases: merging to `main` bumps version via Actions; creating/publishing a GitHub release triggers PyPI publish. **2.0.0** was a manual major bump for enum alignment; see [`CHANGELOG.md`](CHANGELOG.md).

## Conventions when changing code

1. **Minimize scope** — only change what the task requires.
2. **ctypes** — follow existing patterns in `dll_wrapper.py`: set `argtypes` / `restype`; use `c_int16` for var IDs, `c_uint16` for boat index, `c_double` for values where appropriate.
3. **New DLL exports** — confirm against synced `reference/expedition/ExpDLL.h`, add wrapper method, test on Windows with **Expedition running**.
4. **Enums** — `Var` / `SysVar` / `SysBooleanVar` / `SysIntVar` integer values must match channel IDs; run check-enums after header sync; regenerate with `generate_enums_from_headers.py --write` when headers change.
5. **32 vs 64 bit** — Python interpreter bitness must match the Expedition install.
6. **No secrets** in commits; headers stay gitignored.

## Testing notes

- `ExpeditionDLL.from_default_location()` uses registry `HKCU\SOFTWARE\Expedition\Core\Location`.
- Boat `0` is own-ship GPS; lat/lon via DLL on boat 0 may be unavailable (see tests using boat 2 for variation).
- Skipped tests on CI are expected, not failures.

## Quick file map

```
Expedition/           # installable package
scripts/              # header sync, enum generate/check (dev only)
reference/expedition/ # synced .h files (gitignored)
tests/
docs/
```

For human-oriented setup, see [README.md](README.md).
