"""Parse Expedition C channel enums from the proprietary headers.

Shared by the sync, generate and check scripts. The headers are never committed;
they are copied into ``reference/expedition/`` (gitignored) by
``sync_expedition_headers.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCE_DIR = REPO_ROOT / "reference" / "expedition"

# Preprocessor macros treated as undefined. EX_SAIL_AI gates the sail-AI channels,
# which are not present in the shipped DLL (GetExpVarNum returns 418).
DEFINED_MACROS: FrozenSet[str] = frozenset()


@dataclass(frozen=True)
class EnumSpec:
    """One C enum mapped to one Python class."""

    c_name: str
    py_name: str
    header: str
    prefix: str


ENUM_SPECS: List[EnumSpec] = [
    EnumSpec("ExChannels", "Var", "user_channels.h", "Ex"),
    EnumSpec("ExSysChannels", "SysVar", "sys_channels.h", "ExSys"),
    EnumSpec("ExSysBooleanChannels", "SysBooleanVar", "sys_channels.h", "ExSysBool"),
    EnumSpec("ExSysIntChannels", "SysIntVar", "sys_channels.h", "ExSysInt"),
]

REQUIRED_HEADERS = ("ExpDLL.h", "user_channels.h", "sys_channels.h")
OPTIONAL_HEADERS = ("sys_val.h",)


def preprocess(text: str, defines: Iterable[str] = DEFINED_MACROS) -> str:
    """Strip comments and resolve ``#ifdef`` / ``#ifndef`` / ``#else`` / ``#endif``."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    defined = set(defines)
    stack: List[bool] = []
    out: List[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            directive = stripped[1:].strip().split()
            if not directive:
                continue
            keyword = directive[0]
            if keyword == "ifdef":
                stack.append(bool(directive[1:]) and directive[1] in defined)
            elif keyword == "ifndef":
                stack.append(bool(directive[1:]) and directive[1] not in defined)
            elif keyword == "else" and stack:
                stack[-1] = not stack[-1]
            elif keyword == "endif" and stack:
                stack.pop()
            continue
        if all(stack):
            out.append(line)
    return "\n".join(out)


def parse_enum(text: str, c_name: str) -> Dict[str, int]:
    """Return ``{raw_c_member_name: value}`` in declaration order for one enum."""
    processed = preprocess(text)
    match = re.search(
        r"enum\s+" + re.escape(c_name) + r"\s*:\s*\w+\s*\{(.*?)\};", processed, flags=re.S
    )
    if match is None:
        raise ValueError(f"enum {c_name} not found in header")

    values: Dict[str, int] = {}
    next_value = 0
    for raw in match.group(1).split(","):
        token = raw.strip()
        if not token:
            continue
        if "=" in token:
            name, expr = (part.strip() for part in token.split("=", 1))
            value = values[expr] if expr in values else int(expr, 0)
        else:
            name = token
            value = next_value
        if not re.fullmatch(r"[A-Za-z_]\w*", name):
            raise ValueError(f"unexpected token in {c_name}: {token!r}")
        values[name] = value
        next_value = value + 1
    return values


def python_member_name(spec: EnumSpec, c_member: str) -> str:
    """Mechanical C-to-Python member name, e.g. ``ExSysBoatLength`` -> ``BoatLength``."""
    if spec.c_name == "ExChannels":
        # ExChannels members use "Ex" (or the all-caps "EX" in EXCANFastPacketErrors).
        if c_member.startswith("Ex") or c_member.startswith("EX"):
            return c_member[2:]
        return c_member
    if c_member.startswith(spec.prefix):
        return c_member[len(spec.prefix) :]
    if c_member.startswith("Ex"):
        # ExNumSysChannels -> NumSysChannels
        return c_member[2:]
    raise ValueError(f"cannot derive Python name for {c_member} in {spec.c_name}")


def load_enums(reference_dir: Path = REFERENCE_DIR) -> Dict[str, Dict[str, int]]:
    """Return ``{py_class_name: {python_member_name: value}}`` from the reference headers."""
    cache: Dict[str, str] = {}
    result: Dict[str, Dict[str, int]] = {}
    for spec in ENUM_SPECS:
        if spec.header not in cache:
            cache[spec.header] = (reference_dir / spec.header).read_text(encoding="utf-8")
        raw = parse_enum(cache[spec.header], spec.c_name)
        result[spec.py_name] = {
            python_member_name(spec, name): value for name, value in raw.items()
        }
    return result


def find_missing_headers(reference_dir: Path = REFERENCE_DIR) -> Optional[List[str]]:
    """Return the required header names that are not present, or None if all exist."""
    missing = [name for name in REQUIRED_HEADERS if not (reference_dir / name).is_file()]
    return missing or None
