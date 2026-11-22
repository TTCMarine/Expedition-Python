"""Pre-load checks for ExpDLL.dll.

Everything except ``load_dll`` is pure Python (``struct`` and ``platform``), so the
checks run on macOS and in unit tests. Expedition ships two builds:

* ``ExpeditionARM/`` - ExpDLL.dll is ARM64 (0xAA64), companion ``libcrypto-3-arm64.dll``.
* ``ExpeditionX64/`` - ExpDLL.dll is AMD64 (0x8664), companion ``libcrypto-3-x64.dll``.

The DLL and the Python interpreter must share a native machine type. An AMD64 Python
can run under emulation on ARM64 Windows but still cannot load an ARM64 DLL.
"""

from __future__ import annotations

import ctypes
import os
import platform
import struct
import warnings
from typing import Optional

from .errors import ExpeditionLoadError, ExpeditionVersionWarning

DLL_NAME = "ExpDLL.dll"
EXE_NAME = "Expedition.exe"

MACHINE_I386 = 0x014C
MACHINE_AMD64 = 0x8664
MACHINE_ARM64 = 0xAA64

MACHINE_ARCHITECTURES = {MACHINE_AMD64: "AMD64", MACHINE_ARM64: "ARM64"}
SUPPORTED_ARCHITECTURES = ("AMD64", "ARM64")
COMPANION_LIBCRYPTO = {
    "AMD64": "libcrypto-3-x64.dll",
    "ARM64": "libcrypto-3-arm64.dll",
}
OTHER_BUILD_FOLDER = {"AMD64": "ExpeditionX64", "ARM64": "ExpeditionARM"}
ERROR_MOD_NOT_FOUND = 126  # WinError: a DLL or one of its dependencies was not found


def read_pe_machine(path: str) -> int:
    """Return the COFF ``Machine`` field of a Windows PE file.

    Raises ExpeditionLoadError if the file is not a PE image or is truncated.
    """
    try:
        with open(path, "rb") as handle:
            dos_header = handle.read(0x40)
            if len(dos_header) < 0x40 or dos_header[:2] != b"MZ":
                raise ExpeditionLoadError(f"{path} is not a Windows PE file (missing MZ header)")
            (pe_offset,) = struct.unpack_from("<I", dos_header, 0x3C)
            handle.seek(pe_offset)
            signature = handle.read(6)
    except OSError as exc:
        if isinstance(exc, ExpeditionLoadError):
            raise
        raise ExpeditionLoadError(f"Could not read {path}: {exc}") from exc

    if len(signature) < 6 or signature[:4] != b"PE\x00\x00":
        raise ExpeditionLoadError(f"{path} is not a Windows PE file (missing PE signature)")
    (machine,) = struct.unpack_from("<H", signature, 4)
    return int(machine)


def dll_architecture(machine: int) -> Optional[str]:
    """Map a PE machine type to ``'AMD64'`` or ``'ARM64'``; None if unsupported."""
    return MACHINE_ARCHITECTURES.get(machine)


def interpreter_architecture() -> str:
    """Describe the running Python: ``'AMD64'``, ``'ARM64'``, ``'32-bit'`` or the raw machine name."""
    if struct.calcsize("P") != 8:
        return "32-bit"
    machine = platform.machine().upper()
    if machine in ("AMD64", "X86_64"):
        return "AMD64"
    if machine in ("ARM64", "AARCH64"):
        return "ARM64"
    return machine or "unknown"


def _mismatch_message(dll_arch: str, python_arch: str) -> str:
    message = (
        f"ExpDLL.dll is {dll_arch} but this Python is {python_arch}. "
        f"A {dll_arch} Expedition DLL needs a native {dll_arch} Python."
    )
    if dll_arch == "ARM64" and python_arch == "AMD64":
        message += (
            " x64 Python cannot load ARM64 DLLs: install native ARM64 Python, "
            "or point at the ExpeditionX64 build."
        )
    elif dll_arch == "AMD64" and python_arch == "ARM64":
        message += (
            " Install AMD64 Python (it runs under emulation on ARM64 Windows), "
            "or point at the ExpeditionARM build."
        )
    else:
        message += " Install a Python that matches the DLL, or point at the matching build."
    return message


def check_dll_architecture(dll_path: str, python_arch: Optional[str] = None) -> str:
    """Check that the DLL is a supported build for this interpreter; return its architecture."""
    machine = read_pe_machine(dll_path)
    dll_arch = dll_architecture(machine)
    if dll_arch is None:
        raise ExpeditionLoadError(
            f"{dll_path} has PE machine type 0x{machine:04X}. "
            "Only AMD64 (0x8664) and ARM64 (0xAA64) Expedition builds are supported; "
            "32-bit builds are not."
        )
    current = python_arch or interpreter_architecture()
    if current != dll_arch:
        raise ExpeditionLoadError(_mismatch_message(dll_arch, current))
    return dll_arch


def check_companion_library(dll_dir: str, dll_arch: str) -> None:
    """Raise ExpeditionLoadError if the libcrypto companion DLL is not beside ExpDLL.dll."""
    companion = COMPANION_LIBCRYPTO[dll_arch]
    if not os.path.exists(os.path.join(dll_dir, companion)):
        raise ExpeditionLoadError(
            f"{companion} was not found in {dll_dir}. The {dll_arch} Expedition build needs it "
            "beside ExpDLL.dll (along with mfc140u.dll)."
        )


def warn_if_exe_mismatch(dll_dir: str, dll_arch: str) -> None:
    """Warn when Expedition.exe beside the DLL is a different architecture from the DLL."""
    exe_path = os.path.join(dll_dir, EXE_NAME)
    if not os.path.isfile(exe_path):
        return
    try:
        exe_arch = dll_architecture(read_pe_machine(exe_path))
    except ExpeditionLoadError:
        return
    if exe_arch is not None and exe_arch != dll_arch:
        warnings.warn(
            f"{EXE_NAME} is {exe_arch} but {DLL_NAME} is {dll_arch}. "
            "Mixed Expedition builds in one folder are not supported.",
            ExpeditionVersionWarning,
            stacklevel=3,
        )


def preflight(dll_path: str) -> str:
    """Run every check that does not load the DLL. Returns the DLL architecture."""
    dll_arch = check_dll_architecture(dll_path)
    dll_dir = os.path.dirname(dll_path)
    check_companion_library(dll_dir, dll_arch)
    warn_if_exe_mismatch(dll_dir, dll_arch)
    return dll_arch


def load_dll(dll_path: str, dll_arch: str):
    """Load ExpDLL.dll with ``ctypes.windll`` and translate loader failures."""
    windll = getattr(ctypes, "windll", None)
    if windll is None:
        raise ExpeditionLoadError("Expedition-Python can only load ExpDLL.dll on Windows")
    try:
        return windll.LoadLibrary(dll_path)
    except OSError as exc:
        if getattr(exc, "winerror", None) == ERROR_MOD_NOT_FOUND:
            companion = COMPANION_LIBCRYPTO[dll_arch]
            raise ExpeditionLoadError(
                f"Could not load {dll_path} (WinError 126: a dependency is missing). "
                f"Check that {companion} and mfc140u.dll are in the same folder as "
                f"{DLL_NAME}."
            ) from exc
        raise ExpeditionLoadError(f"Could not load {dll_path}: {exc}") from exc
