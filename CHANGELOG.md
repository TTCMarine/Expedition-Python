# Changelog

## 2.1.0

Minor release: support Expedition **EXP_API_VERSION 1.2** (ExpeditionX) while keeping compatibility with legacy ExpDLL installs.

### Added

- Optional export probing at `ExpeditionDLL` init — works on both legacy and 1.2 DLLs.
- `ExpeditionDLL.api_version` (`"legacy"` or `"1.2"`), `has_batch_vars`, and `has_exp_var2` capability flags.
- `ExpeditionAPIError` when a method requires a DLL export that is not present.
- Python fallbacks for `set_exp_vars()` / `get_exp_vars()` (and boat position helpers) using `SetExpVar` / `GetExpVar` when batch exports are removed.
- `ExVal` type and `get_exp_var2()` / `set_exp_var2()` for ExpDLL 1.2 (`SetExpVar2` / `GetExpVar2`).

### Changed

- `get_variation()` uses legacy `GetVariation` when exported; otherwise falls back to `Var.MagVar` via scratch boat (as before).

### Deprecated on ExpDLL API 1.2

These Python methods remain but raise `ExpeditionAPIError` on 1.2 DLLs (exports removed): `set_var_precision`, `get_var_precision`, `set_boat_name`, `get_boat_colour`, `set_boat_colour`, `get_ais_dangerous_cpa`, `ping_mark`, `create_active_route`, `add_mark_to_active_route`.

### Development

- Optional header sync for `sys_val.h` when Expedition ships it (layout currently verified against ExpDLL 1.2 on Windows).
- After Expedition upgrade: sync headers → check-enums → review `ExpDLL.h` exports → update wrapper → run tests.

## 2.0.0

Breaking release: Python enums are regenerated from Expedition channel headers so **names and integer values match** `user_channels.h` and `sys_channels.h`.

### Fixed

- `SysVar`, `SysBooleanVar`, and `SysIntVar` member order and values now align with Expedition (previous layouts used incorrect indices after `AltTwa`, breaking `get_sys_var()` for many channels).

### Removed (examples)

- `SysVar`: `WhatIfSet`, `WhatIfDrift`, `WhatIfTwd`, `WhatIfTws`, `Spare0`, `AutoLegRange`, `StartRSTime`, `StartRSAng`, …, `StripChartWand*`, `Cursor*`, `StartStrbLatX`, …
- `Var`: `Leeway`, `Heel`, `Trim`, `DTargBsp` (and aliases `Roll = Heel`, `Pitch = Trim`)
- `SysBooleanVar`: `Spare0`, `ErrorLogging`, … (replaced by header names such as `AutoPan`, `AutoPalette`)
- `SysIntVar`: `Utc` at index 0 (replaced by `Theme`, etc.)

### Renamed (examples)

- `Var.Leeway` → `Var.Lwy`
- `Var.DTargBsp` → `Var.DeltaTargBsp`
- `Var.Heel` / `Var.Roll` → `Var.Roll` (primary name from `ExRoll`)
- `Var.Trim` / `Var.Pitch` → `Var.Pitch` (primary name from `ExPitch`)
- `SysVar.StripChartWandLat0` → `SysVar.WandLat0`
- `SysVar.CursorTime` → `SysVar.MouseTime`

### Development

- Regenerate enums after syncing headers: `uv run python scripts/generate_enums_from_headers.py --write`
- Verify alignment: `uv run python scripts/check_enums_against_headers.py`

## 1.1.x

See [GitHub releases](https://github.com/TTCMarine/Expedition-Python/releases).
