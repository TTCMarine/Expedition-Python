"""Expedition ExVal type (EXP_API_VERSION 1.2+).

Layout matches ``struct ExVal { int64_t time; double value; }`` as inferred from
``GetExpVar2`` / ``SetExpVar2`` on ExpDLL 1.2. Sync ``sys_val.h`` locally when
Expedition ships it and verify against that header.
"""

from __future__ import annotations

from ctypes import Structure, c_double, c_int64
from dataclasses import dataclass

__all__ = ["ExVal", "ExValStruct"]


class ExValStruct(Structure):
    """ctypes layout passed to SetExpVar2 / GetExpVar2."""

    _fields_ = [("time", c_int64), ("value", c_double)]


@dataclass(frozen=True)
class ExVal:
    """Typed channel value for ExpDLL 1.2 Var2 APIs."""

    value: float
    time: int = 0

    def to_struct(self) -> ExValStruct:
        return ExValStruct(time=self.time, value=self.value)

    @classmethod
    def from_struct(cls, struct: ExValStruct) -> ExVal:
        return cls(value=struct.value, time=struct.time)
