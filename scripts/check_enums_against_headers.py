"""Verify Expedition/enums.py matches reference/expedition/*.h.

Exits 0 when every member name and integer value matches, 1 otherwise.
Skips with exit 0 and a notice when no headers are synced, so CI without
proprietary headers is unaffected.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from _header_enums import REFERENCE_DIR, find_missing_headers, load_enums  # noqa: E402


def compare(expected: Dict[str, Dict[str, int]], enums_module) -> List[str]:
    problems: List[str] = []
    for class_name, members in expected.items():
        py_class = getattr(enums_module, class_name, None)
        if py_class is None:
            problems.append(f"missing class {class_name}")
            continue
        actual = {name: int(member.value) for name, member in py_class.__members__.items()}
        for name, value in members.items():
            if name not in actual:
                problems.append(f"{class_name}.{name}: missing in enums.py (header value {value})")
            elif actual[name] != value:
                problems.append(f"{class_name}.{name}: enums.py={actual[name]} header={value}")
        for name in actual:
            if name not in members:
                problems.append(f"{class_name}.{name}: in enums.py but not in headers")
    return problems


def main() -> int:
    missing = find_missing_headers(REFERENCE_DIR)
    if missing:
        print(f"Skipping enum check: headers not synced ({', '.join(missing)}).")
        return 0

    expected = load_enums(REFERENCE_DIR)
    enums_module = importlib.import_module("Expedition.enums")
    problems = compare(expected, enums_module)
    if problems:
        print("Enum mismatches:")
        for problem in problems:
            print(f"  {problem}")
        print("Re-run scripts/generate_enums_from_headers.py --write after reviewing.")
        return 1

    counts = ", ".join(f"{name}={len(members)}" for name, members in expected.items())
    print(f"OK: enums.py matches headers ({counts})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
