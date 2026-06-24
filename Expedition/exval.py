"""Expedition ExVal type (EXP_API_VERSION 1.2+).

Layout matches ``sys_val.h``: ``int8_t type`` (``e_ValType``) plus an 8-byte union
(``bool``, ``double``, ``int32``, WinRT ``int64`` ticks, or ``char[8]``).
"""

from __future__ import annotations

from ctypes import Structure, Union, c_bool, c_char, c_double, c_int8, c_int32, c_int64
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import IntEnum
from typing import Union as TypingUnion

__all__ = [
    "ExVal",
    "ExValStruct",
    "ExValUnion",
    "ValType",
    "WINRT_EPOCH",
    "datetime_to_winrt_ticks",
    "timedelta_to_winrt_ticks",
    "winrt_ticks_to_datetime",
    "winrt_ticks_to_timedelta",
]

WINRT_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
_TICKS_PER_SECOND = 10_000_000


class ValType(IntEnum):
    """Mirrors ``enum e_ValType`` from Expedition ``time_dev.h``."""

    Bool = 0
    Double = 1
    Int32 = 2
    Int64 = 3
    String = 4


class ExValUnion(Union):
    _fields_ = [
        ("b", c_bool),
        ("d", c_double),
        ("i32", c_int32),
        ("t", c_int64),
        ("s", c_char * 8),
    ]


class ExValStruct(Structure):
    """ctypes layout passed to SetExpVar2 / GetExpVar2."""

    _fields_ = [("type", c_int8), ("_pad", c_char * 7), ("u", ExValUnion)]


def datetime_to_winrt_ticks(dt: datetime) -> int:
    """Convert a datetime to WinRT 100ns ticks since 1601-01-01 UTC."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    delta = dt - WINRT_EPOCH
    return int(delta.total_seconds() * _TICKS_PER_SECOND)


def winrt_ticks_to_datetime(ticks: int) -> datetime:
    """Convert WinRT 100ns ticks since 1601-01-01 UTC to a timezone-aware datetime."""
    return WINRT_EPOCH + timedelta(microseconds=ticks / 10)


def timedelta_to_winrt_ticks(td: timedelta) -> int:
    """Convert a timedelta to WinRT 100ns tick count (time span)."""
    return int(td.total_seconds() * _TICKS_PER_SECOND)


def winrt_ticks_to_timedelta(ticks: int) -> timedelta:
    """Convert WinRT 100ns tick count to a timedelta (time span)."""
    return timedelta(microseconds=ticks / 10)


@dataclass(frozen=True)
class ExVal:
    """Typed channel value for ExpDLL 1.2 Var2 APIs."""

    type: ValType
    payload: TypingUnion[bool, float, int, str]

    @classmethod
    def from_bool(cls, value: bool) -> ExVal:
        return cls(ValType.Bool, value)

    @classmethod
    def from_double(cls, value: float) -> ExVal:
        return cls(ValType.Double, value)

    @classmethod
    def from_int32(cls, value: int) -> ExVal:
        return cls(ValType.Int32, value)

    @classmethod
    def from_ticks(cls, ticks: int) -> ExVal:
        """WinRT 100ns ticks (time instant or span)."""
        return cls(ValType.Int64, ticks)

    @classmethod
    def from_datetime(cls, dt: datetime) -> ExVal:
        return cls.from_ticks(datetime_to_winrt_ticks(dt))

    @classmethod
    def from_timedelta(cls, td: timedelta) -> ExVal:
        return cls.from_ticks(timedelta_to_winrt_ticks(td))

    @classmethod
    def from_string(cls, value: str) -> ExVal:
        if len(value) > 8:
            raise ValueError("string value must be 8 characters or less")
        return cls(ValType.String, value)

    def as_bool(self) -> bool:
        self._require_type(ValType.Bool)
        return bool(self.payload)

    def as_double(self) -> float:
        self._require_type(ValType.Double)
        return float(self.payload)

    def as_int32(self) -> int:
        self._require_type(ValType.Int32)
        return int(self.payload)

    def as_ticks(self) -> int:
        self._require_type(ValType.Int64)
        return int(self.payload)

    def as_datetime(self) -> datetime:
        return winrt_ticks_to_datetime(self.as_ticks())

    def as_timedelta(self) -> timedelta:
        return winrt_ticks_to_timedelta(self.as_ticks())

    def as_string(self) -> str:
        self._require_type(ValType.String)
        return str(self.payload)

    def _require_type(self, expected: ValType) -> None:
        if self.type is not expected:
            raise TypeError(f"expected ValType.{expected.name}, got ValType.{self.type.name}")

    def to_struct(self) -> ExValStruct:
        struct = ExValStruct()
        struct.type = int(self.type)
        if self.type is ValType.Bool:
            struct.u.b = self.as_bool()
        elif self.type is ValType.Double:
            struct.u.d = self.as_double()
        elif self.type is ValType.Int32:
            struct.u.i32 = self.as_int32()
        elif self.type is ValType.Int64:
            struct.u.t = self.as_ticks()
        elif self.type is ValType.String:
            encoded = self.as_string().encode("ascii", errors="replace")[:8]
            struct.u.s = encoded.ljust(8, b"\0")
        return struct

    @classmethod
    def from_struct(cls, struct: ExValStruct) -> ExVal:
        val_type = ValType(int(struct.type))
        if val_type is ValType.Bool:
            return cls.from_bool(bool(struct.u.b))
        if val_type is ValType.Double:
            return cls.from_double(float(struct.u.d))
        if val_type is ValType.Int32:
            return cls.from_int32(int(struct.u.i32))
        if val_type is ValType.Int64:
            return cls.from_ticks(int(struct.u.t))
        if val_type is ValType.String:
            raw = bytes(struct.u.s)
            return cls.from_string(raw.split(b"\0", 1)[0].decode("ascii", errors="replace"))
        raise ValueError(f"unsupported ValType value: {struct.type}")
