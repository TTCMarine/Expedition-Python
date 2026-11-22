"""Copy Expedition C headers into reference/expedition/ (gitignored).

Source directory, in order of precedence:
  1. --install-dir
  2. EXPEDITION_INSTALL_DIR
  3. Registry HKCU\\SOFTWARE\\Expedition\\Core\\Location (Windows only)
  4. Common Program Files locations

The source may be an install root or one of its build folders (ExpeditionARM,
ExpeditionX64). When several locations hold the same header with different
content, the script stops and reports the difference instead of picking one.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _header_enums import OPTIONAL_HEADERS, REFERENCE_DIR, REQUIRED_HEADERS  # noqa: E402

BUILD_SUBFOLDERS = ("ExpeditionX64", "ExpeditionARM")
PROGRAM_FILES_CANDIDATES = (
    r"C:\Program Files\Expedition\Expedition",
    r"C:\Program Files (x86)\Expedition\Expedition",
)


def _registry_location() -> Optional[str]:
    if sys.platform != "win32":
        return None
    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Expedition\Core")
        value, _ = winreg.QueryValueEx(key, "Location")
        winreg.CloseKey(key)
        return str(value)
    except OSError:
        return None


def resolve_install_dir(cli_value: Optional[str]) -> Path:
    candidates: List[str] = []
    if cli_value:
        candidates.append(cli_value)
    env_value = os.environ.get("EXPEDITION_INSTALL_DIR")
    if env_value:
        candidates.append(env_value)
    registry_value = _registry_location()
    if registry_value:
        candidates.append(registry_value)
    candidates.extend(PROGRAM_FILES_CANDIDATES)

    for candidate in candidates:
        path = Path(candidate)
        if path.is_dir() and _has_any_header(path):
            return path
    raise SystemExit(
        "Could not find Expedition headers. Pass --install-dir or set EXPEDITION_INSTALL_DIR."
    )


def _has_any_header(directory: Path) -> bool:
    search = [directory] + [directory / name for name in BUILD_SUBFOLDERS]
    return any((folder / "ExpDLL.h").is_file() for folder in search)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def locate_headers(install_dir: Path) -> Dict[str, Path]:
    """Find each header, checking the root and both build folders.

    Raises SystemExit if a required header is missing or if locations disagree.
    """
    search_dirs = [install_dir] + [install_dir / name for name in BUILD_SUBFOLDERS]
    search_dirs = [folder for folder in search_dirs if folder.is_dir()]

    chosen: Dict[str, Path] = {}
    for name in REQUIRED_HEADERS + OPTIONAL_HEADERS:
        found = [folder / name for folder in search_dirs if (folder / name).is_file()]
        if not found:
            if name in REQUIRED_HEADERS:
                raise SystemExit(f"Required header {name} not found under {install_dir}")
            print(f"note: optional header {name} not present, skipping")
            continue
        hashes = {str(path): _sha256(path) for path in found}
        if len(set(hashes.values())) > 1:
            details = "\n".join(f"  {path}  sha256={digest}" for path, digest in hashes.items())
            raise SystemExit(
                f"{name} differs between locations; resolve before syncing:\n{details}"
            )
        chosen[name] = found[0]
    return chosen


def sync(install_dir: Path, destination: Path = REFERENCE_DIR) -> List[str]:
    chosen = locate_headers(install_dir)
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for name, source in chosen.items():
        shutil.copyfile(source, destination / name)
        copied.append(f"{name} <- {source}")
    return copied


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--install-dir", help="Expedition install root or build folder")
    parser.add_argument("--destination", default=str(REFERENCE_DIR), help=argparse.SUPPRESS)
    args = parser.parse_args(argv)

    install_dir = resolve_install_dir(args.install_dir)
    copied = sync(install_dir, Path(args.destination))
    print(f"Synced from {install_dir}:")
    for line in copied:
        print(f"  {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
