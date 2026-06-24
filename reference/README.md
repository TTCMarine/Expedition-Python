# Expedition reference headers (local only)

Expedition C headers are **proprietary** to [Expedition Marine](https://www.expeditionmarine.com/). They are not included in the PyPI package and must not be committed to this repository.

## Syncing headers

On Windows, with Expedition installed:

```bash
uv run python scripts/sync_expedition_headers.py
```

This copies from your Expedition install directory (registry `HKCU\SOFTWARE\Expedition\Core\Location`, or `EXPEDITION_INSTALL_DIR`, or common Program Files paths) into `reference/expedition/`:

| File | Required |
|------|----------|
| `ExpDLL.h` | Yes — DLL API for [`Expedition/dll_wrapper.py`](../Expedition/dll_wrapper.py) |
| `user_channels.h` | Yes — `ExChannels` / `Var` |
| `sys_channels.h` | Yes — `ExSysChannels`, `ExSysBooleanChannels`, `ExSysIntChannels` |
| `sys_val.h` | Optional — `ExVal` layout for `SetExpVar2` / `GetExpVar2` |

`e_ValType` values (`Bool`, `Double`, `Int32`, `Int64`, `String`) are defined in Expedition's `time_dev.h`; the Python `ValType` enum in [`Expedition/exval.py`](../Expedition/exval.py) must stay aligned if that header changes.

The `reference/expedition/` directory is listed in [`.gitignore`](../.gitignore).

After syncing headers, review `ExpDLL.h` exports and update [`Expedition/dll_wrapper.py`](../Expedition/dll_wrapper.py) if the API changed.

## Regenerating and checking Python enums

After syncing headers:

```bash
uv run python scripts/generate_enums_from_headers.py --write
uv run python scripts/check_enums_against_headers.py
```

`generate_enums_from_headers.py` rewrites [`Expedition/enums.py`](../Expedition/enums.py) using mechanical C-to-Python naming. `check_enums_against_headers.py` must exit 0 before you rely on enum values.

## Override install path

```bash
set EXPEDITION_INSTALL_DIR=C:\Path\To\Expedition\Expedition
uv run python scripts/sync_expedition_headers.py --install-dir "C:\Path\To\Expedition\Expedition"
```

See [AGENTS.md](../AGENTS.md) for the full workflow.
