# Changelog

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
