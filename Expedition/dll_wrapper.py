import ctypes
import os
from ctypes import POINTER, c_bool, c_char_p, c_double, c_int, c_ubyte, c_uint16
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

from .enums import SysBooleanVar, SysVar, Var
from .exval import ExVal, ExValStruct

EXPEDITION_DLL_REG_KEY = r"SOFTWARE\Expedition\Core"

# Boat index used when reading MagVar via set_boat_position
# boat 0 cannot always read Lat/Lon due to GPS source selection
_VARIATION_SCRATCH_BOAT = 2
_OLE_DATE_EPOCH = datetime(1899, 12, 30)


class ExpeditionAPIError(Exception):
    """Raised when the loaded ExpDLL does not export a function required for an API."""


def _datetime_to_ole_date(dt: datetime) -> float:
    """OLE DATE: days since 1899-12-30 (legacy GetVariation)."""
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    delta = dt - _OLE_DATE_EPOCH
    return delta.days + (delta.seconds + delta.microseconds / 1e6) / 86400.0


__all__ = ["ExpeditionAPIError", "ExpeditionDLL", "get_expedition_location"]


def get_expedition_location():
    import winreg

    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, EXPEDITION_DLL_REG_KEY)
    value, _ = winreg.QueryValueEx(key, "Location")
    return value


class ExpeditionDLL:
    """
    Wrapper for the Expedition DLL

    This class provides a Python interface to the Expedition DLL.
    """

    @staticmethod
    def from_default_location():
        """
        Create an instance of the ExpeditionDLL class using the default installation location
        :return: an instance of the ExpeditionDLL class
        """
        expedition_location = get_expedition_location()
        return ExpeditionDLL(expedition_location)

    def __init__(self, exp_install_dir):
        """
        Create an instance of the ExpeditionDLL class
        :param exp_install_dir: The directory where Expedition is installed (e.g. C:\\Program Files (x86)\\Expedition)
        """
        self.exp_install_dir = exp_install_dir
        dll_name = "ExpDLL.dll"
        dll_path = os.path.join(exp_install_dir, dll_name)
        if not os.path.exists(dll_path):
            raise FileNotFoundError(f"Could not find {dll_name} in {exp_install_dir}")
        self.exp_dll = ctypes.windll.LoadLibrary(dll_path)

        self._bind_core_exports()
        self._bind_optional_exports()

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

    @property
    def number_of_vars(self) -> int:
        """
        Get the number of Expedition variables
        :return: The number of Expedition variables
        """
        return int(self._GetExpVarNum())

    def get_exp_var_name(self, var: Var) -> str:
        """
        Get the name of an Expedition variable
        :param var: enumeration of the variable
        :return: the name of the variable
        """
        name = ctypes.create_string_buffer(16)
        self._GetExpVarName(c_uint16(int(var)), name)
        return name.value.decode("utf-8")

    def set_exp_user_var_name(self, var: Var, name):
        """
        Set the name of a user variable
        :param var: enumeration of the variable
        :param name: the name of the variable
        :return: None
        """
        # name must be a string of length 16 or less
        if len(name) > 16:
            raise ValueError("name must be 16 characters or less")

        if (0 <= var <= 31) or (Var.User0 <= var <= Var.User31):
            self._SetExpUserVarName(c_uint16(int(var)), name.encode("utf-8"))
        else:
            raise ValueError("var must be between 0 and 31 or between Var.User0 and Var.User31")

    def set_var_precision(self, var: Var, precision: int):
        """
        Set precision for a user variable.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._SetVarPrecision is not None, "SetVarPrecision", "set_var_precision"
        )
        if (0 <= var <= 31) or (Var.User0 <= var <= Var.User31):
            self._SetVarPrecision(c_uint16(int(var)), c_uint16(precision))
        else:
            raise ValueError("var must be between 0 and 31 or between Var.User0 and Var.User31")

    def get_var_precision(self, var: Var) -> int:
        """
        Get precision for a user variable.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(
            self._GetVarPrecision is not None, "GetVarPrecision", "get_var_precision"
        )
        if not ((0 <= var <= 31) or (Var.User0 <= var <= Var.User31)):
            raise ValueError("var must be between 0 and 31 or between Var.User0 and Var.User31")
        precision = c_uint16()
        self._GetVarPrecision(c_uint16(int(var)), ctypes.byref(precision))
        return int(precision.value)

    def set_exp_var_value(self, var: Var, value: float, boat=0):
        """
        Set the value of an Expedition variable
        :param var: enumeration of the variable
        :param value: the value to set
        :param boat: the boat number to set the variable for (default 0)
        """
        self._SetExpVar(c_uint16(int(var)), c_double(value), c_uint16(boat))

    def set_exp_var2(self, var: Var, value: ExVal, boat=0):
        """
        Set a channel value using ExpDLL 1.2 SetExpVar2 (typed ExVal).

        Requires ExpDLL API 1.2+.
        """
        self._require_export(self.has_exp_var2, "SetExpVar2", "set_exp_var2")
        self._SetExpVar2(c_uint16(int(var)), value.to_struct(), c_uint16(boat))

    def set_exp_var_by_name(self, name: str, value: float, boat=0):
        """
        Set the value of an Expedition variable by name
        :param name: the name of the variable
        :param value: the value to set
        :param boat: the boat number to set the variable for (default 0)
        """
        try:
            var_id = Var[name]
        except KeyError:
            raise ValueError(f"Variable name '{name}' not found")
        self._SetExpVar(c_uint16(int(var_id)), c_double(value), c_uint16(boat))

    def get_exp_var_value(self, var: Var, boat=0) -> Optional[float]:
        """
        Get the value of an Expedition variable
        :param var: enumeration of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable
        """
        value = c_double()
        id_alt = c_uint16()
        valid = self._GetExpVar(
            c_uint16(int(var)), ctypes.byref(value), c_uint16(boat), ctypes.byref(id_alt)
        )
        if valid:
            return value.value
        else:
            return None

    def get_exp_var2(self, var: Var, boat=0) -> Optional[ExVal]:
        """
        Get a channel value using ExpDLL 1.2 GetExpVar2 (typed ExVal).

        Requires ExpDLL API 1.2+.
        """
        self._require_export(self.has_exp_var2, "GetExpVar2", "get_exp_var2")
        value = ExValStruct()
        id_alt = c_uint16()
        valid = self._GetExpVar2(
            c_uint16(int(var)), ctypes.byref(value), c_uint16(boat), ctypes.byref(id_alt)
        )
        if valid:
            return ExVal.from_struct(value)
        return None

    def get_exp_var_value_by_name(self, name: str, boat=0):
        """
        Get the value of an Expedition variable by name
        :param name: the name of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable
        """
        var_id = Var[name]
        value = c_double()
        id_alt = c_uint16()
        valid = self._GetExpVar(
            c_uint16(int(var_id)), ctypes.byref(value), c_uint16(boat), ctypes.byref(id_alt)
        )
        if valid:
            return value.value
        return None

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
        if self._SetExpVars is not None:
            var_array = (c_uint16 * len(var_list))(*(int(v) for v in var_list))
            value_array = (c_double * len(value_list))(*value_list)
            self._SetExpVars(var_array, value_array, c_uint16(len(var_list)), c_uint16(boat))
            return
        for var, value in zip(var_list, value_list):
            self.set_exp_var_value(var, value, boat)

    def get_exp_vars(self, var_list: List[Var], boat=0) -> Optional[List[float]]:
        """
        Get the values of a list of Expedition variables
        :param var_list: list of variables to get
        :param boat: boat number to get the variables for (default 0)
        :return: list of values
        """
        if self._GetExpVars is not None:
            var_array = (c_uint16 * len(var_list))(*(int(v) for v in var_list))
            value_array = (c_double * len(var_list))()
            valid = self._GetExpVars(
                var_array, value_array, c_uint16(len(var_list)), c_uint16(boat)
            )
            if valid:
                return list(value_array)
            return None
        values: List[float] = []
        for var in var_list:
            value = self.get_exp_var_value(var, boat)
            if value is None:
                return None
            values.append(value)
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
        value = c_double()
        valid = self._GetSysVar(c_uint16(int(var)), ctypes.byref(value))
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
        value = c_bool()
        valid = self._GetSysBool(c_uint16(int(var)), ctypes.byref(value))
        if valid:
            return value.value
        else:
            return None

    def get_number_of_boats(self) -> int:
        """
        Get the number of boats in the Expedition
        :return: maximum boat number
        """
        return int(self._GetBoatNum())

    def set_boat_name(self, boat: int, name: str):
        """
        Set the name of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._SetBoatName is not None, "SetBoatName", "set_boat_name")
        if len(name) > 32:
            raise ValueError("name must be 32 characters or less")
        self._SetBoatName(c_uint16(boat), name.encode("utf-8"))

    def get_boat_colour(self, boat: int) -> Tuple[int, int, int]:
        """
        Get the colour of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._GetBoatColour is not None, "GetBoatColour", "get_boat_colour")
        r = c_ubyte()
        g = c_ubyte()
        b = c_ubyte()
        self._GetBoatColour(c_uint16(boat), ctypes.byref(r), ctypes.byref(g), ctypes.byref(b))
        return r.value, g.value, b.value

    def set_boat_colour(self, boat: int, r: int, g: int, b: int):
        """
        Set the colour of a boat.

        Deprecated on ExpDLL API 1.2 (export removed); requires legacy ExpDLL.
        """
        self._require_export(self._SetBoatColour is not None, "SetBoatColour", "set_boat_colour")
        self._SetBoatColour(c_uint16(boat), c_ubyte(r), c_ubyte(g), c_ubyte(b))

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
        self, lat: float, lon: float, date: Optional[datetime] = None
    ) -> Optional[float]:
        """
        Get magnetic variation (degrees) at a position.

        Uses legacy ExpDLL GetVariation when exported; otherwise reads Var.MagVar
        after setting position on a scratch boat (Expedition must be running).
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

        boat = _VARIATION_SCRATCH_BOAT
        prev_position = self.get_boat_position(boat)
        try:
            self.set_boat_position(boat, (lat, lon))
            magvar = self.get_exp_var_value(Var.MagVar, boat)
        finally:
            if prev_position is not None:
                self.set_boat_position(boat, prev_position)

        return magvar
