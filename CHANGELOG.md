# Changelog

## 3.0.0

Breaking release: enum IDs now match the November Expedition headers, invalid arguments raise `ValueError` instead of being sent to the DLL, and there is an opt-in strict mode. This is a clean break: there are no deprecated aliases for the renamed members.

### Breaking changes

- **Channel IDs shifted.** `Var.NumChannels` is 418 (was 414). Code that stores raw integer IDs must be updated.
- **`Var` additions:** `BowLat` (414), `BowLon` (415), `SternLat` (416), `SternLon` (417), `AltMax` (alias of `Alt9`) and `UserMax` (alias of `User31`).
- **`Var` rename:** `ExSysGpsTimeDelta` is now `SysGpsTimeDelta` (256).
- **`Var` rename:** `EXCANFastPacketErrors` is now `CANFastPacketErrors`.
- **`SysVar` removals:** `BowLat`, `BowLon`, `SternLat` and `SternLon` were removed from `SysVar`, so every member from `PrevMarkBrg` onward moved down by 4 (for example `CalTwa` is now 57, was 61). `SysVar.NumSysChannels` is 76 (was 80).
- **`SysBooleanVar` renames:** the stray `l` prefix is removed (`lAutoPan` is now `AutoPan`, `lMax` is now `Max`, and so on). Values are unchanged.
- **`SysBooleanVar` and `SysIntVar` are now `IntEnum`** (were `Enum`), so members compare and convert as integers. `.value` still works.
- **User variable names are limited to 15 bytes** (was 16). Names are encoded in the ANSI code page on Windows (`mbcs`) and as ASCII elsewhere.
- **`set_exp_user_var_name` and `set_var_precision` / `get_var_precision`** reject channels that are not user variables. Previously `Var.Bsp` (value 1) was accepted and renamed `User1`.
- **Bad arguments raise `ValueError`** before anything reaches the DLL: channel IDs outside the range for the loaded DLL, boats outside `0..get_number_of_boats()-1`, system variable IDs outside range, colour components outside 0..255, and unknown channel names. `get_exp_var_value_by_name` previously raised `KeyError` for unknown names; it now raises `ValueError`, like the setter.
- **Writing to `Var.Utc`** raises `ValueError`, because the DLL ignores that write.
- **Load failures** raise `ExpeditionLoadError` (an `OSError` subclass) with an explanation, instead of a raw `OSError`. This covers the wrong bitness or architecture, a missing companion `libcrypto` DLL (WinError 126), and a registry lookup failure.

### Added

- **Two Expedition builds are supported:** `ExpeditionARM/` (ARM64 DLL) and `ExpeditionX64/` (AMD64 DLL). `ExpeditionDLL` reads the PE machine type of `ExpDLL.dll` and checks it against the Python interpreter before loading. ARM64 DLLs need native ARM64 Python. AMD64 DLLs need AMD64 Python, which runs under emulation on ARM64 Windows.
- **Strict mode:** `ExpeditionDLL(folder, strict=True)` and `ExpeditionDLL.from_default_location(strict=True)`. In strict mode, writes raise `ExpeditionNotRunningError` when Expedition is not running, and writes that do not read back raise `ExpeditionWriteError`. Default behaviour is unchanged.
- `ExpeditionDLL.is_running()`: a best-effort check that reads `Var.Utc`. Not documented by Expedition, so treat it as a heuristic.
- `ExpeditionDLL.get_exp_var_ex(var, boat)` returns `ExpVarReading(value, resolved_var)`. `resolved_var` shows which channel supplied the value for `Alt0` to `Alt9`.
- `GPS_BOAT0_CHANNELS`: writes to these channels on boat 0 emit `ExpeditionWriteWarning`. Expedition ignores them unless the GPS source is set to the DLL.
- `ExpeditionVersionWarning` when `GetExpVarNum()` does not match `Var.NumChannels`. This means the installed Expedition and this package were built against different headers.
- `Expedition.errors` module with `ExpeditionAPIError`, `ExpeditionLoadError`, `ExpeditionNotRunningError`, `ExpeditionWriteError`, `ExpeditionWriteWarning` and `ExpeditionVersionWarning`.
- Development scripts in `scripts/`: `sync_expedition_headers.py`, `generate_enums_from_headers.py` and `check_enums_against_headers.py`. These are not shipped in the wheel.
- `py.typed` is now included in the package.

### Changed

- The DLL export counts (`number_of_vars`, `get_number_of_boats()`) are read once at load time instead of on every call.
- `ExpeditionDLL.from_default_location()` raises `ExpeditionLoadError` when Expedition is not registered or the registry value is missing.
- Expedition's registry entry points at whichever build was registered last. If both builds are installed, pass the build folder to `ExpeditionDLL(...)` explicitly.

### Migration

1. Replace integer channel IDs with `Var` members, or regenerate any saved IDs.
2. Rename `ExSysGpsTimeDelta`, `EXCANFastPacketErrors`, `lAutoPan` and similar members (see above).
3. Keep user variable names to 15 bytes or fewer.
4. Catch `ValueError` where you previously relied on the DLL silently ignoring bad input.
5. Use `strict=True` during development to find writes that Expedition drops.

## 2.2.0

Breaking release: `ExVal` now matches the real `sys_val.h` layout and `e_ValType` discriminator.

### Changed

- `ExValStruct` is `int8_t type` + 8-byte union (`bool`, `double`, `int32`, WinRT `int64` ticks, `char[8]`), not the previous guessed `{time, value}` layout.
- `ExVal(value=, time=)` removed. Use typed factories: `ExVal.from_double()`, `ExVal.from_datetime()`, `ExVal.from_ticks()`, `ExVal.from_timedelta()`, etc.
- Time values use **WinRT 100ns ticks** since 1601-01-01 UTC (`e_Int64` / union member `t`), not OLE DATE.
- New `ValType` enum mirrors `e_ValType` (`Bool`, `Double`, `Int32`, `Int64`, `String`).
- WinRT conversion helpers: `datetime_to_winrt_ticks`, `winrt_ticks_to_datetime`, `timedelta_to_winrt_ticks`, `winrt_ticks_to_timedelta`.

### Notes

- Expedition currently uses `e_Double` for most channels and `e_Int64` for time instants and spans; other types are defined for future use.

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
