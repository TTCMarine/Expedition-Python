import ctypes
import math
import operator
import os
import sys
import warnings
from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_ubyte, c_uint16
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, FrozenSet, List, Optional, Sequence, Tuple, Union

from . import _loader
from .enums import SysBooleanVar, SysVar, Var
from .errors import (
    ExpeditionAPIError,
    ExpeditionLoadError,
    ExpeditionNotRunningError,
    ExpeditionVersionWarning,
    ExpeditionWriteError,
    ExpeditionWriteWarning,
)
from .exval import ExVal, ExValStruct, ValType

EXPEDITION_DLL_REG_KEY = r"SOFTWARE\Expedition\Core"

# Boat index used when reading MagVar via set_boat_position
# boat 0 cannot always read Lat/Lon due to GPS source selection
_VARIATION_SCRATCH_BOAT = 2
_OLE_DATE_EPOCH = datetime(1899, 12, 30)

# Value ExpDLL returns for a channel with no valid data.
_INVALID_VALUE = 32767.0
_INVALID_VALUE_TOLERANCE = 1e-3

# User variables: Var.User0..Var.User31 are IDs 172..203 (0xAC..0xCB).
# SetExpUserVarName maps plain indices below 0xAC by adding 0xAC.
_USER_INDEX_MIN = 0
_USER_INDEX_MAX = 31

# ExpDLL stores user variable names in 15 bytes plus a terminator, in the ANSI code page.
USER_VAR_NAME_MAX_BYTES = 15
_BOAT_NAME_MAX_CHARS = 32
_COLOUR_MAX = 255

# Read-back tolerance used in strict mode. Tune on Windows if legitimate writes differ slightly.
_WRITE_READBACK_TOLERANCE = 1e-6

# Channels that Expedition takes from the GPS on boat 0. Writes to these on boat 0 are
# dropped unless the GPS source is set to the DLL (inferred value 3; not verified on Windows).
GPS_BOAT0_CHANNELS: FrozenSet[Var] = frozenset(
    Var[name]
    for name in (
        "GpsMethod",
        "GpsHDOP",
        "GpsPDOP",
        "GpsVDOP",
        "GpsNumber",
        "GpsAge",
        "GpsAltitude",
        "GpsGeoidSeparation",
        "GpsMode",
        "Lat",
        "Lon",
        "Cog",
        "Sog",
        "DiffRefStn",
        "GpsTime",
        "GpsHPE",
        "SysGpsTimeDelta",
        "FuelLevel2",
    )
)

# Alt0..Alt9 share a slot. Expedition resolves them to whichever channel is active, so the
# value read back may legitimately differ from the value written.
_ALTERNATING_CHANNELS: FrozenSet[Var] = frozenset(Var[f"Alt{i}"] for i in range(10))


@dataclass(frozen=True)
class ExpVarReading:
    """A channel value and the channel that actually supplied it.

    ``resolved_var`` differs from the requested channel for alternating channels
    (``Alt0``..``Alt9``), where ExpDLL reports which underlying channel it used.
    """

    value: float
    resolved_var: Union[Var, int]


def _as_index(value, name: str) -> int:
    """Return ``value`` as an int, rejecting bools and non-integers with ValueError."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer, not bool")
    try:
        return operator.index(value)
    except TypeError:
        raise ValueError(f"{name} must be an integer, got {value!r}") from None


def _var_label(var_id: int) -> str:
    try:
        return Var(var_id).name
    except ValueError:
        return str(var_id)


def _is_invalid(value: float) -> bool:
    return abs(value - _INVALID_VALUE) < _INVALID_VALUE_TOLERANCE


_NAME_CODEC = "mbcs" if sys.platform == "win32" else "ascii"


def _encode_user_name(name) -> bytes:
    if not isinstance(name, str):
        raise ValueError("name must be a string")
    try:
        data = name.encode(_NAME_CODEC)
    except UnicodeEncodeError as exc:
        raise ValueError(
            f"name must be encodable as {_NAME_CODEC} (the ANSI code page on Windows): {exc}"
        ) from None
    if len(data) > USER_VAR_NAME_MAX_BYTES:
        raise ValueError(
            f"name must be {USER_VAR_NAME_MAX_BYTES} bytes or fewer in {_NAME_CODEC}; "
            f"got {len(data)} bytes"
        )
    return data


def _user_index_arg(var) -> int:
    """Argument for SetExpUserVarName / SetVarPrecision.

    A ``Var`` member must be ``User0..User31``. A plain int must be a user index 0..31.
    Other channels (for example ``Var.Bsp``, value 1) are rejected because the DLL would
    otherwise rename ``User1``.
    """
    if isinstance(var, Var):
        if not (Var.User0 <= var <= Var.User31):
            raise ValueError(
                f"{var.name} is not a user variable; use Var.User0..Var.User31 or an index 0..31"
            )
        return int(var)
    value = _as_index(var, "var")
    if not (_USER_INDEX_MIN <= value <= _USER_INDEX_MAX):
        raise ValueError(f"user variable index must be between 0 and 31, got {value}")
    return value


def _datetime_to_ole_date(dt: datetime) -> float:
    """OLE DATE: days since 1899-12-30 (legacy GetVariation)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    delta = dt - _OLE_DATE_EPOCH
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400.0


__all__ = [
    "ExpVarReading",
    "ExpeditionAPIError",
    "ExpeditionDLL",
    "ExpeditionLoadError",
    "ExpeditionNotRunningError",
    "ExpeditionVersionWarning",
    "ExpeditionWriteError",
    "ExpeditionWriteWarning",
    "GPS_BOAT0_CHANNELS",
    "get_expedition_location",
]


def get_expedition_location() -> str:
    """Return the Expedition install folder registered for the current user.

    Raises ExpeditionLoadError when not on Windows or when Expedition is not registered.
    If both builds are installed, the registry points at whichever one was registered last;
    pass the build folder to ExpeditionDLL explicitly in that case.
    """
    if sys.platform != "win32":
        raise ExpeditionLoadError(
            "Finding Expedition in the registry requires Windows; pass the install folder "
            "to ExpeditionDLL instead."
        )

    import winreg

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, EXPEDITION_DLL_REG_KEY)
    except OSError as exc:
        raise ExpeditionLoadError(
            f"Expedition is not registered (HKCU\\{EXPEDITION_DLL_REG_KEY} not found). "
            "Install Expedition or pass the install folder to ExpeditionDLL."
        ) from exc
    try:
        value, _ = winreg.QueryValueEx(key, "Location")
    except OSError as exc:
        raise ExpeditionLoadError(
            f"HKCU\\{EXPEDITION_DLL_REG_KEY} has no 'Location' value. "
            "Pass the install folder to ExpeditionDLL."
        ) from exc
    finally:
        winreg.CloseKey(key)
    return str(value)


class ExpeditionDLL:
    """
    Wrapper for the Expedition DLL

    This class provides a Python interface to the Expedition DLL.

    By default, writes that Expedition ignores are silent, as they are in the DLL itself.
    Pass ``strict=True`` to raise ExpeditionNotRunningError when Expedition is not running
    and ExpeditionWriteError when a written value does not read back.
    """

    @staticmethod
    def from_default_location(strict: bool = False):
        """
        Create an instance of the ExpeditionDLL class using the default installation location
        :param strict: raise on writes Expedition would ignore (see class docstring)
        :return: an instance of the ExpeditionDLL class
        """
        expedition_location = get_expedition_location()
        return ExpeditionDLL(expedition_location, strict=strict)

    def __init__(self, exp_install_dir, strict: bool = False):
        """
        Create an instance of the ExpeditionDLL class
        :param exp_install_dir: The folder containing ExpDLL.dll (the install folder or an
            ExpeditionARM / ExpeditionX64 build folder)
        :param strict: raise on writes Expedition would ignore (see class docstring)
        """
        self.exp_install_dir = exp_install_dir
        self._strict = bool(strict)
        dll_name = _loader.DLL_NAME
        dll_path = os.path.join(exp_install_dir, dll_name)
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"Could not find {dll_name} in {exp_install_dir}")
        self.dll_architecture = _loader.preflight(dll_path)
        self.exp_dll = _loader.load_dll(dll_path, self.dll_architecture)

        self._bind_core_exports()
        self._bind_optional_exports()

        self._num_vars = int(self._GetExpVarNum())
        self._num_boats = int(self._GetBoatNum())
        if self._num_vars != int(Var.NumChannels):
            warnings.warn(
                f"ExpDLL reports {self._num_vars} channels but this version of Expedition-Python "
                f"was built for {int(Var.NumChannels)}. Channel IDs may refer to different "
                "channels. Upgrade Expedition-Python to match your Expedition install.",
                ExpeditionVersionWarning,
                stacklevel=2,
            )

    @property
    def strict(self) -> bool:
        """True when writes raise on ignored values (see class docstring)."""
        return self._strict

    @staticmethod
    def _bind_fn(dll, name, argtypes, restype=None):
        fn = getattr(dll, name, None)
        if fn is None:
            return None
        fn.argtypes = argtypes
        if restype is not None:
            fn.restype = restype
        return fn

    def _bind_core_exports(self):
        self._GetExpVarNum = self._bind_fn(self.exp_dll, "GetExpVarNum", [], c_int)
        self._GetExpVarName = self._bind_fn(
            self.exp_dll, "GetExpVarName", [c_uint16, POINTER(ctypes.c_char)]
        )
        self._SetExpUserVarName = self._bind_fn(
            self.exp_dll, "SetExpUserVarName", [c_uint16, c_char_p]
        )
        self._SetExpVar = self._bind_fn(self.exp_dll, "SetExpVar", [c_uint16, c_double, c_uint16])
        self._GetExpVar = self._bind_fn(
            self.exp_dll,
            "GetExpVar",
            [c_uint16, POINTER(c_double), c_uint16, POINTER(c_uint16)],
            c_bool,
        )
        self._GetSysVar = self._bind_fn(
            self.exp_dll, "GetSysVar", [c_uint16, POINTER(c_double)], c_bool
        )
        self._GetSysBool = self._bind_fn(
            self.exp_dll, "GetSysBool", [c_uint16, POINTER(c_bool)], c_bool
        )
        self._GetBoatNum = self._bind_fn(self.exp_dll, "GetBoatNum", [], c_int)
        self._SetMOB = self._bind_fn(self.exp_dll, "SetMOB", [c_double, c_double])

        missing = [
            name
            for name, fn in (
                ("GetExpVarNum", self._GetExpVarNum),
                ("GetExpVarName", self._GetExpVarName),
                ("SetExpUserVarName", self._SetExpUserVarName),
                ("SetExpVar", self._SetExpVar),
                ("GetExpVar", self._GetExpVar),
                ("GetSysVar", self._GetSysVar),
                ("GetSysBool", self._GetSysBool),
                ("GetBoatNum", self._GetBoatNum),
                ("SetMOB", self._SetMOB),
            )
            if fn is None
        ]
        if missing:
            raise ExpeditionAPIError(f"ExpDLL is missing required exports: {', '.join(missing)}")

    def _bind_optional_exports(self):
        self._SetVarPrecision = self._bind_fn(self.exp_dll, "SetVarPrecision", [c_uint16, c_uint16])
        self._GetVarPrecision = self._bind_fn(
            self.exp_dll, "GetVarPrecision", [c_uint16, POINTER(c_uint16)]
        )
        self._SetExpVars = self._bind_fn(
            self.exp_dll,
            "SetExpVars",
            [POINTER(c_uint16), POINTER(c_double), c_uint16, c_uint16],
        )
        self._GetExpVars = self._bind_fn(
            self.exp_dll,
            "GetExpVars",
            [POINTER(c_uint16), POINTER(c_double), c_uint16, c_uint16],
            c_bool,
        )
        self._SetBoatName = self._bind_fn(self.exp_dll, "SetBoatName", [c_uint16, c_char_p])
        self._GetBoatColour = self._bind_fn(
            self.exp_dll,
            "GetBoatColour",
            [c_uint16, POINTER(c_ubyte), POINTER(c_ubyte), POINTER(c_ubyte)],
        )
        self._SetBoatColour = self._bind_fn(
            self.exp_dll, "SetBoatColour", [c_uint16, c_ubyte, c_ubyte, c_ubyte]
        )
        self._GetVariation = self._bind_fn(
            self.exp_dll,
            "GetVariation",
            [ctypes.c_double, c_double, c_double, POINTER(c_double)],
            c_bool,
        )
        self._GetAisDangerousCPA = self._bind_fn(
            self.exp_dll,
            "GetAisDangerousCPA",
            [POINTER(c_bool), POINTER(ctypes.c_wchar), c_uint16],
        )
        self._PingMark = self._bind_fn(
            self.exp_dll, "PingMark", [c_char_p, c_double, c_double, c_bool]
        )
        self._CreateActiveRoute = self._bind_fn(
            self.exp_dll, "CreateActiveRoute", [c_char_p, c_bool]
        )
        self._AddMarkToActiveRoute = self._bind_fn(
            self.exp_dll,
            "AddMarkToActiveRoute",
            [c_char_p, c_double, c_double, c_bool, c_bool],
        )
        self._SetExpVar2 = self._bind_fn(
            self.exp_dll, "SetExpVar2", [c_uint16, ExValStruct, c_uint16]
        )
        self._GetExpVar2 = self._bind_fn(
            self.exp_dll,
            "GetExpVar2",
            [c_uint16, POINTER(ExValStruct), c_uint16, POINTER(c_uint16)],
            c_bool,
        )

    @property
    def api_version(self) -> str:
        """``'1.2'`` when SetExpVar2 is exported, otherwise ``'legacy'``."""
        return "1.2" if self._SetExpVar2 is not None else "legacy"

    @property
    def has_exp_var2(self) -> bool:
        return self._SetExpVar2 is not None and self._GetExpVar2 is not None

    @property
    def has_batch_vars(self) -> bool:
        return self._SetExpVars is not None and self._GetExpVars is not None

    def _require_export(self, available: bool, export_name: str, method_name: str) -> None:
        if not available:
            raise ExpeditionAPIError(
                f"{method_name} requires ExpDLL export {export_name}, "
                f"not available in API version {self.api_version}"
            )

    # ------------------------------------------------------------------
    # Argument validation. Bad arguments raise ValueError before the DLL is called,
    # because the DLL ignores or misreads them without reporting an error.
    # ------------------------------------------------------------------

    @property
    def number_of_vars(self) -> int:
        """
        Get the number of Expedition variables (read once when the DLL is loaded)
        :return: The number of Expedition variables
        """
        return self._num_vars

    def _var_id(self, var, *, write: bool) -> int:
        value = _as_index(var, "var")
        low = 1 if write else 0  # the DLL ignores writes to ID 0 (Utc)
        if not (low <= value < self._num_vars):
            raise ValueError(
                f"var must be between {low} and {self._num_vars - 1} for this Expedition, "
                f"got {value}"
            )
        return value

    def _boat_id(self, boat) -> int:
        value = _as_index(boat, "boat")
        if not (0 <= value < self._num_boats):
            raise ValueError(
                f"boat must be between 0 and {self._num_boats - 1} for this Expedition, "
                f"got {value}"
            )
        return value

    @staticmethod
    def _sys_var_id(var) -> int:
        value = _as_index(var, "var")
        limit = int(SysVar.NumSysChannels)
        if not (0 <= value < limit):
            raise ValueError(f"system var must be between 0 and {limit - 1}, got {value}")
        return value

    @staticmethod
    def _sys_bool_id(var) -> int:
        value = _as_index(var, "var")
        limit = int(SysBooleanVar.Max)
        if not (0 <= value < limit):
            raise ValueError(f"system boolean var must be between 0 and {limit - 1}, got {value}")
        return value

    def _lookup_name(self, name: str) -> Var:
        if not isinstance(name, str):
            raise ValueError(f"variable name must be a string, got {name!r}")
        try:
            return Var[name]
        except KeyError:
            raise ValueError(f"Variable name '{name}' not found") from None

    def _warn_if_gps_write_on_boat0(self, var_id: int, boat: int) -> None:
        if boat == 0 and var_id in GPS_BOAT0_CHANNELS:
            warnings.warn(
                f"{Var(var_id).name} on boat 0 is taken from the GPS. Expedition drops writes to "
                "it unless the GPS source is set to the DLL. Writes to boat 1 or higher are not "
                "affected.",
                ExpeditionWriteWarning,
                stacklevel=4,
            )

    def _before_write(self, writes: Sequence[Tuple[int, float, int]]) -> None:
        """Run the strict-mode running check and the boat-0 GPS warning before a write."""
        if self._strict and not self.is_running():
            raise ExpeditionNotRunningError(
                "Expedition is not running, so this write would be dropped. Start Expedition, "
                "or create the ExpeditionDLL without strict=True to keep the silent behaviour."
            )
        for var_id, _value, boat in writes:
            self._warn_if_gps_write_on_boat0(var_id, boat)

    def _after_write(self, writes: Sequence[Tuple[int, float, int]]) -> None:
        """In strict mode, read each written value back and check it was applied."""
        if not self._strict:
            return
        for var_id, value, boat in writes:
            if var_id in _ALTERNATING_CHANNELS:
                continue
            reading = self._read_raw(var_id, boat)
            if reading is None or not math.isclose(
                reading[0],
                value,
                rel_tol=_WRITE_READBACK_TOLERANCE,
                abs_tol=_WRITE_READBACK_TOLERANCE,
            ):
                applied = "no valid value" if reading is None else f"{reading[0]}"
                raise ExpeditionWriteError(
                    f"Expedition did not apply {_var_label(var_id)} on boat {boat}: wrote "
                    f"{value}, read back {applied}. Likely causes: boat 0 GPS channel with the "
                    "GPS source not set to the DLL, a channel Expedition derives itself, or "
                    "playback/log mode."
                )

    def _read_raw(self, var_id: int, boat: int) -> Optional[Tuple[float, int]]:
        """Read a channel as ``(value, resolved_id)``, or None when there is no valid value.

        On ExpDLL API 1.2 the read goes through ``GetExpVar2``, and the double it returns is
        used directly. A typed value that is not a double (for example Int32 or Int64 ticks)
        cannot be represented faithfully as a float here, so the legacy ``GetExpVar`` read is
        used for those channels, as before.
        """
        if self.has_exp_var2:
            struct = ExValStruct()
            id_alt_typed = c_uint16()
            valid = self._GetExpVar2(
                c_uint16(var_id), ctypes.byref(struct), c_uint16(boat), ctypes.byref(id_alt_typed)
            )
            if not valid:
                return None
            if int(struct.type) == int(ValType.Double):
                return struct.u.d, id_alt_typed.value

        value = c_double()
        id_alt = c_uint16()
        valid = self._GetExpVar(
            c_uint16(var_id), ctypes.byref(value), c_uint16(boat), ctypes.byref(id_alt)
        )
        if valid:
            return value.value, id_alt.value
        return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_running(self) -> bool:
        """
        Best-effort check that Expedition is running.

        Reads ``Var.Utc`` on boat 0 and treats the invalid-value sentinel as "not running".
        This is inferred from the DLL, not documented. Whether Utc keeps updating during log
        playback is not verified.
        """
        reading = self._read_raw(int(Var.Utc), 0)
        return reading is not None and not _is_invalid(reading[0])

    def get_exp_var_name(self, var: Var) -> str:
        """
        Get the name of an Expedition variable
        :param var: enumeration of the variable
        :return: the name of the variable
        """
        var_id = self._var_id(var, write=False)
        name = ctypes.create_string_buffer(16)
        self._GetExpVarName(c_uint16(var_id), name)
        return name.value.decode(_NAME_CODEC, errors="replace")

    def set_exp_user_var_name(self, var: Var, name: str):
        """
        Set the name of a user variable
        :param var: a user variable (Var.User0..Var.User31) or an index 0..31
        :param name: the name, at most 15 bytes in the ANSI code page (ASCII on macOS)
        :return: None
        """
        index = _user_index_arg(var)
        data = _encode_user_name(name)
        self._SetExpUserVarName(c_uint16(index), data)

    def set_var_precision(self, var: Var, precision: int):
        """
        Set precision for a user variable.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._SetVarPrecision is not None, "SetVarPrecision", "set_var_precision"
        )
        index = _user_index_arg(var)
        self._SetVarPrecision(c_uint16(index), c_uint16(precision))

    def get_var_precision(self, var: Var) -> int:
        """
        Get precision for a user variable.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._GetVarPrecision is not None, "GetVarPrecision", "get_var_precision"
        )
        index = _user_index_arg(var)
        precision = c_uint16()
        self._GetVarPrecision(c_uint16(index), ctypes.byref(precision))
        return int(precision.value)

    def set_exp_var_value(self, var: Var, value: float, boat=0):
        """
        Set the value of an Expedition variable
        :param var: enumeration of the variable
        :param value: the value to set
        :param boat: the boat number to set the variable for (default 0)
        """
        var_id = self._var_id(var, write=True)
        boat_id = self._boat_id(boat)
        writes = [(var_id, float(value), boat_id)]
        self._before_write(writes)
        self._SetExpVar(c_uint16(var_id), c_double(value), c_uint16(boat_id))
        self._after_write(writes)

    def set_exp_var2(self, var: Var, value: ExVal, boat=0):
        """
        Set a channel value using ExpDLL 1.2 SetExpVar2 (typed ExVal).

        Pass ``ExVal.from_double(...)``, ``ExVal.from_datetime(...)``, etc.
        Requires ExpDLL API 1.2+. Strict mode checks that Expedition is running but does not
        read the value back.
        """
        self._require_export(self.has_exp_var2, "SetExpVar2", "set_exp_var2")
        var_id = self._var_id(var, write=True)
        boat_id = self._boat_id(boat)
        self._before_write([(var_id, 0.0, boat_id)])
        self._SetExpVar2(c_uint16(var_id), value.to_struct(), c_uint16(boat_id))

    def set_exp_var_by_name(self, name: str, value: float, boat=0):
        """
        Set the value of an Expedition variable by name
        :param name: the name of the variable
        :param value: the value to set
        :param boat: the boat number to set the variable for (default 0)
        """
        self.set_exp_var_value(self._lookup_name(name), value, boat)

    def get_exp_var_value(self, var: Var, boat=0) -> Optional[float]:
        """
        Get the value of an Expedition variable

        On ExpDLL API 1.2 this uses ``GetExpVar2`` and returns the double it holds. Other
        typed channels, and legacy DLLs, use ``GetExpVar``.

        :param var: enumeration of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable, or None when Expedition has no valid value
        """
        var_id = self._var_id(var, write=False)
        boat_id = self._boat_id(boat)
        reading = self._read_raw(var_id, boat_id)
        return None if reading is None else reading[0]

    def get_exp_var_ex(self, var: Var, boat=0) -> Optional[ExpVarReading]:
        """
        Get a channel value and the channel ExpDLL used to supply it.

        For ``Alt0``..``Alt9`` the ``resolved_var`` field shows which underlying channel
        Expedition read. For other channels it equals ``var``.
        :return: ExpVarReading, or None when Expedition has no valid value
        """
        var_id = self._var_id(var, write=False)
        boat_id = self._boat_id(boat)
        reading = self._read_raw(var_id, boat_id)
        if reading is None:
            return None
        value, resolved_id = reading
        try:
            resolved: Union[Var, int] = Var(resolved_id)
        except ValueError:
            resolved = resolved_id
        return ExpVarReading(value=value, resolved_var=resolved)

    def get_exp_var2(self, var: Var, boat=0) -> Optional[ExVal]:
        """
        Get a channel value using ExpDLL 1.2 GetExpVar2 (typed ExVal).

        Requires ExpDLL API 1.2+.
        """
        self._require_export(self.has_exp_var2, "GetExpVar2", "get_exp_var2")
        var_id = self._var_id(var, write=False)
        boat_id = self._boat_id(boat)
        value = ExValStruct()
        id_alt = c_uint16()
        valid = self._GetExpVar2(
            c_uint16(var_id), ctypes.byref(value), c_uint16(boat_id), ctypes.byref(id_alt)
        )
        if valid:
            return ExVal.from_struct(value)
        return None

    def get_exp_var_value_by_name(self, name: str, boat=0):
        """
        Get the value of an Expedition variable by name
        :param name: the name of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable, or None when Expedition has no valid value
        """
        return self.get_exp_var_value(self._lookup_name(name), boat)

    def set_exp_vars(self, var_list: List[Var], value_list: List[float], boat=0):
        """
        Set the values of a list of Expedition variables
        :param var_list: list of variables to set
        :param value_list: values to set
        :param boat: boat number to set the variables for (default 0)
        :return: None
        """
        if len(var_list) != len(value_list):
            raise ValueError("vars and values must be the same length")
        boat_id = self._boat_id(boat)
        writes = [
            (self._var_id(var, write=True), float(value), boat_id)
            for var, value in zip(var_list, value_list)
        ]
        self._before_write(writes)
        if self._SetExpVars is not None:
            var_array = (c_uint16 * len(writes))(*(w[0] for w in writes))
            value_array = (c_double * len(writes))(*(w[1] for w in writes))
            self._SetExpVars(var_array, value_array, c_uint16(len(writes)), c_uint16(boat_id))
        else:
            for var_id, value, _ in writes:
                self._SetExpVar(c_uint16(var_id), c_double(value), c_uint16(boat_id))
        self._after_write(writes)

    def get_exp_vars(self, var_list: List[Var], boat=0) -> Optional[List[float]]:
        """
        Get the values of a list of Expedition variables
        :param var_list: list of variables to get
        :param boat: boat number to get the variables for (default 0)
        :return: list of values
        """
        var_ids = [self._var_id(var, write=False) for var in var_list]
        boat_id = self._boat_id(boat)
        if self._GetExpVars is not None:
            var_array = (c_uint16 * len(var_ids))(*var_ids)
            value_array = (c_double * len(var_ids))()
            valid = self._GetExpVars(
                var_array, value_array, c_uint16(len(var_ids)), c_uint16(boat_id)
            )
            if valid:
                return list(value_array)
            return None
        values: List[float] = []
        for var_id in var_ids:
            reading = self._read_raw(var_id, boat_id)
            if reading is None:
                return None
            values.append(reading[0])
        return values

    def set_exp_vars_dict(self, var_dict: Dict[Var, float], boat=0):
        """
        Set the values of a dictionary of Expedition variables
        :param var_dict: dictionary of variables to set
        :param boat: boat number to set the variables for (default 0)
        :return: None
        """
        var_list = list(var_dict.keys())
        value_list = list(var_dict.values())
        self.set_exp_vars(var_list, value_list, boat)

    def get_exp_vars_dict(self, var_list: List[Var], boat=0) -> Optional[Dict[Var, float]]:
        """
        Get the values of a list of Expedition variables
        :param var_list: list of variables to get
        :param boat: boat number to get the variables for (default 0)
        :return: dictionary of values
        """
        values = self.get_exp_vars(var_list, boat)
        if values:
            return dict(zip(var_list, values))
        else:
            return None

    def get_sys_var(self, var: SysVar) -> Optional[float]:
        """
        Get the value of a system variable
        :param var: system variable enumeration
        :return: value
        """
        var_id = self._sys_var_id(var)
        value = c_double()
        valid = self._GetSysVar(c_uint16(var_id), ctypes.byref(value))
        if valid:
            return value.value
        else:
            return None

    def get_sys_bool(self, var: SysBooleanVar) -> Optional[bool]:
        """
        Get the value of a system boolean variable
        :param var: system boolean variable enumeration
        :return: value
        """
        var_id = self._sys_bool_id(var)
        value = c_bool()
        valid = self._GetSysBool(c_uint16(var_id), ctypes.byref(value))
        if valid:
            return value.value
        else:
            return None

    def get_number_of_boats(self) -> int:
        """
        Get the number of boats in the Expedition (read once when the DLL is loaded)
        :return: maximum boat number
        """
        return self._num_boats

    def set_boat_name(self, boat: int, name: str):
        """
        Set the name of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._SetBoatName is not None, "SetBoatName", "set_boat_name")
        boat_id = self._boat_id(boat)
        if not isinstance(name, str):
            raise ValueError("name must be a string")
        if len(name) > _BOAT_NAME_MAX_CHARS:
            raise ValueError(f"name must be {_BOAT_NAME_MAX_CHARS} characters or less")
        self._SetBoatName(c_uint16(boat_id), name.encode("utf-8"))

    def get_boat_colour(self, boat: int) -> Tuple[int, int, int]:
        """
        Get the colour of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._GetBoatColour is not None, "GetBoatColour", "get_boat_colour")
        boat_id = self._boat_id(boat)
        r = c_ubyte()
        g = c_ubyte()
        b = c_ubyte()
        self._GetBoatColour(c_uint16(boat_id), ctypes.byref(r), ctypes.byref(g), ctypes.byref(b))
        return r.value, g.value, b.value

    def set_boat_colour(self, boat: int, r: int, g: int, b: int):
        """
        Set the colour of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._SetBoatColour is not None, "SetBoatColour", "set_boat_colour")
        boat_id = self._boat_id(boat)
        components = []
        for component_name, component in (("r", r), ("g", g), ("b", b)):
            value = _as_index(component, component_name)
            if not (0 <= value <= _COLOUR_MAX):
                raise ValueError(f"{component_name} must be between 0 and 255, got {value}")
            components.append(value)
        red, green, blue = components
        self._SetBoatColour(c_uint16(boat_id), c_ubyte(red), c_ubyte(green), c_ubyte(blue))

    def get_ais_dangerous_cpa(self) -> Tuple[bool, str]:
        """
        Get dangerous AIS CPA state and target name.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._GetAisDangerousCPA is not None,
            "GetAisDangerousCPA",
            "get_ais_dangerous_cpa",
        )
        dangerous = c_bool()
        name = ctypes.create_unicode_buffer(32)
        self._GetAisDangerousCPA(ctypes.byref(dangerous), name, c_uint16(len(name)))
        return bool(dangerous.value), name.value

    def set_boat_position(self, boat: int, lat_lon: Tuple[float, float]):
        """
        Set the position of a boat
        :param boat: the number of the boat
        :param lat_lon: tuple of latitude and longitude
        :return:
        """
        self.set_exp_vars([Var.Lat, Var.Lon], list(lat_lon), boat)

    def get_boat_position(self, boat: int) -> Union[Tuple[float, float], None]:
        """
        Get the position of a boat
        :param boat: the number of the boat
        :return: tuple of latitude and longitude
        """
        values = self.get_exp_vars([Var.Lat, Var.Lon], boat)
        if values is None:
            return None
        if len(values) == 2 and all(isinstance(x, float) for x in values):
            return values[0], values[1]
        else:
            return None

    def set_mob(self, lat: float, lon: float):
        """
        Set the MOB position
        :param lat: latitude
        :param lon: longitude
        :return:
        """
        self._SetMOB(c_double(lat), c_double(lon))

    def ping_mark(self, name: str, lat: float, lon: float, save: bool):
        """
        Ping a mark.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._PingMark is not None, "PingMark", "ping_mark")
        self._PingMark(name.encode("utf-8"), c_double(lat), c_double(lon), c_bool(save))

    def create_active_route(self, name: str, save: bool = True):
        """
        Create an active route.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._CreateActiveRoute is not None, "CreateActiveRoute", "create_active_route"
        )
        self._CreateActiveRoute(name.encode("utf-8"), c_bool(save))

    def add_mark_to_active_route(
        self, name: str, lat: float, lon: float, locked: bool = True, save: bool = True
    ):
        """
        Add a mark to the active route.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._AddMarkToActiveRoute is not None,
            "AddMarkToActiveRoute",
            "add_mark_to_active_route",
        )
        self._AddMarkToActiveRoute(
            name.encode("utf-8"), c_double(lat), c_double(lon), c_bool(locked), c_bool(save)
        )

    def get_variation(
        self,
        lat: float,
        lon: float,
        date: Optional[datetime] = None,
        allow_scratch_boat: bool = False,
    ) -> Optional[float]:
        """
        Get magnetic variation (degrees) at a position.

        Uses the ExpDLL ``GetVariation`` export when present. This export is absent on
        ExpDLL API 1.2.

        Without the export, the only other source is ``Var.MagVar`` on a scratch boat. That
        route writes Lat/Lon to boat 2 and restores the previous position afterwards, so it
        has side effects on a running Expedition. It is therefore used only when
        ``allow_scratch_boat=True``; otherwise ExpeditionAPIError is raised.

        :param lat: latitude in degrees
        :param lon: longitude in degrees
        :param date: date for the calculation (default: now)
        :param allow_scratch_boat: permit the scratch-boat fallback described above
        :return: variation in degrees, or None if Expedition gave no value
        """
        if self._GetVariation is not None:
            if date is None:
                date = datetime.now()
            ole_date = _datetime_to_ole_date(date)
            variation = c_double()
            success = self._GetVariation(
                c_double(ole_date), c_double(lat), c_double(lon), ctypes.byref(variation)
            )
            if success:
                return variation.value
            if not allow_scratch_boat:
                return None
        elif not allow_scratch_boat:
            raise ExpeditionAPIError(
                "get_variation needs the GetVariation export, which ExpDLL API 1.2 does not "
                f"provide (API version {self.api_version}). Pass allow_scratch_boat=True to "
                f"write the position to boat {_VARIATION_SCRATCH_BOAT} temporarily and read "
                "Var.MagVar instead."
            )

        boat = _VARIATION_SCRATCH_BOAT
        prev_position = self.get_boat_position(boat)
        try:
            self.set_boat_position(boat, (lat, lon))
            magvar = self.get_exp_var_value(Var.MagVar, boat)
        finally:
            if prev_position is not None:
                self.set_boat_position(boat, prev_position)

        return magvar
