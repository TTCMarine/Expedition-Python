import winreg
import ctypes
import os
from ctypes import c_int16, c_double, c_uint16, c_char_p, c_bool, POINTER
from typing import List, Tuple, Union, Dict
from .enums import Var, SysVar, SysBooleanVar


EXPEDITION_DLL_REG_KEY = r'SOFTWARE\Expedition\Core'


__all__ = ['ExpeditionDLL']


def get_expedition_location():
    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, EXPEDITION_DLL_REG_KEY)
    value, _ = winreg.QueryValueEx(key, 'Location')
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
        dll_name = 'ExpDLL.dll'
        dll_path = os.path.join(exp_install_dir, dll_name)
        self.exp_dll = ctypes.CDLL(dll_path)

        # Define return types and argument types for the functions
        self.exp_dll.GetExpVarNum.argtypes = [POINTER(c_int16)]
        self.exp_dll.GetExpVarName.argtypes = [c_int16, ctypes.c_char_p]
        self.exp_dll.SetExpUserVarName.argtypes = [c_int16, ctypes.c_char_p]
        self.exp_dll.SetExpVar.argtypes = [c_int16, c_double, c_uint16]
        self.exp_dll.GetExpVar.argtypes = [c_int16, POINTER(c_double), c_uint16, POINTER(c_int16)]
        self.exp_dll.SetExpVars.argtypes = [POINTER(c_int16), POINTER(c_double), c_int16, c_uint16]
        self.exp_dll.GetExpVars.argtypes = [POINTER(c_int16), POINTER(c_double), c_int16, c_uint16]
        self.exp_dll.GetSysVar.argtypes = [c_int16, POINTER(c_double)]
        self.exp_dll.GetSysBool.argtypes = [c_int16, POINTER(c_bool)]
        self.exp_dll.GetBoatNum.argtypes = [POINTER(c_int16)]
        self.exp_dll.SetBoatName.argtypes = [c_uint16, c_char_p]
        self.exp_dll.GetBoatColour.argtypes = [c_uint16, POINTER(c_uint16), POINTER(c_uint16), POINTER(c_uint16)]
        self.exp_dll.SetBoatColour.argtypes = [c_uint16, c_uint16, c_uint16, c_uint16]
        self.exp_dll.GetVariation.argtypes = [ctypes.c_double, c_double, c_double, POINTER(c_double)]
        self.exp_dll.GetAisDangerousCPA.argtypes = [POINTER(c_bool), ctypes.c_wchar_p]
        self.exp_dll.SetMOB.argtypes = [c_double, c_double]
        self.exp_dll.PingMark.argtypes = [c_char_p, c_double, c_double, c_bool]
        self.exp_dll.CreateActiveRoute.argtypes = [c_char_p, c_bool]
        self.exp_dll.AddMarkToActiveRoute.argtypes = [c_char_p, c_double, c_double, c_bool, c_bool]

    # Now you can define Python functions that wrap the DLL functions
    @property
    def number_of_vars(self) -> int:
        """
        Get the number of Expedition variables
        :return: The number of Expedition variables
        """
        num = c_int16()
        self.exp_dll.GetExpVarNum(ctypes.byref(num))
        return num.value

    def get_exp_var_name(self, var: Var) -> str:
        """
        Get the name of an Expedition variable
        :param var: enumeration of the variable
        :return: the name of the variable
        """
        name = ctypes.create_string_buffer(16)
        self.exp_dll.GetExpVarName(c_int16(var), name)
        return name.value.decode('utf-8')

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
            self.exp_dll.SetExpUserVarName(c_int16(var), name.encode('utf-8'))
        else:
            raise ValueError("var must be between 0 and 31 or between Var.User0 and Var.User31")

    def set_exp_var_value(self, var: Var, value: float, boat=0):
        """
        Set the value of an Expedition variable
        :param var: enumeration of the variable
        :param value: the value to set
        :param boat: the boat number to set the variable for (default 0)
        """
        self.exp_dll.SetExpVar(c_int16(var), c_double(value), c_uint16(boat))

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
        self.exp_dll.SetExpVar(c_int16(var_id), c_double(value), c_uint16(boat))

    def get_exp_var_value(self, var: Var, boat=0):
        """
        Get the value of an Expedition variable
        :param var: enumeration of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable
        """
        value = c_double()
        self.exp_dll.GetExpVar(c_int16(var), ctypes.byref(value), c_uint16(boat), None)
        return value.value

    def get_exp_var_value_by_name(self, name: str, boat=0):
        """
        Get the value of an Expedition variable by name
        :param name: the name of the variable
        :param boat: the boat number to get the variable for (default 0)
        :return: value of the variable
        """
        var_id = Var[name]
        value = c_double()
        self.exp_dll.GetExpVar(c_int16(var_id), ctypes.byref(value), c_uint16(boat), None)
        return value.value

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
        var_array = (c_int16 * len(var_list))(*var_list)
        value_array = (c_double * len(value_list))(*value_list)
        self.exp_dll.SetExpVars(var_array, value_array, c_int16(len(var_list)), c_uint16(boat))

    def get_exp_vars(self, var_list: List[Var], boat=0) -> List[float]:
        """
        Get the values of a list of Expedition variables
        :param var_list: list of variables to get
        :param boat: boat number to get the variables for (default 0)
        :return: list of values
        """
        var_array = (c_int16 * len(var_list))(*var_list)
        value_array = (c_double * len(var_list))()
        self.exp_dll.GetExpVars(var_array, value_array, c_int16(len(var_list)), c_uint16(boat))
        return list(value_array)

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

    def get_exp_vars_dict(self, var_list: List[Var], boat=0) -> Dict[Var, float]:
        """
        Get the values of a list of Expedition variables
        :param var_list: list of variables to get
        :param boat: boat number to get the variables for (default 0)
        :return: dictionary of values
        """
        values = self.get_exp_vars(var_list, boat)
        return dict(zip(var_list, values))

    def get_sys_var(self, var: SysVar) -> float:
        """
        Get the value of a system variable
        :param var: system variable enumeration
        :return: value
        """
        value = c_double()
        self.exp_dll.GetSysVar(c_int16(var), ctypes.byref(value))
        return value.value

    def get_sys_bool(self, var: SysBooleanVar) -> bool:
        """
        Get the value of a system boolean variable
        :param var: system boolean variable enumeration
        :return: value
        """
        value = c_bool()
        self.exp_dll.GetSysBool(c_int16(var), ctypes.byref(value))
        return value.value

    def get_number_of_boats(self) -> int:
        """
        Get the number of boats in the Expedition
        :return: maximum boat number
        """
        num = c_int16()
        self.exp_dll.GetBoatNum(ctypes.byref(num))
        return num.value

    def set_boat_name(self, boat: int, name: str):
        """
        Set the name of a boat
        :param boat:
        :param name:
        :return:
        """
        self.exp_dll.SetBoatName(c_uint16(boat), name.encode('utf-8'))

    def get_boat_colour(self, boat: int) -> Tuple[int, int, int]:
        """
        Get the colour of a boat
        :param boat:
        :return: r, g, b colour values
        """
        r = c_uint16()
        g = c_uint16()
        b = c_uint16()
        self.exp_dll.GetBoatColour(c_uint16(boat), ctypes.byref(r), ctypes.byref(g), ctypes.byref(b))
        return r.value, g.value, b.value

    def set_boat_colour(self, boat: int, r: int, g: int, b: int):
        """
        Set the colour of a boat
        :param boat:
        :param r: red
        :param g: green
        :param b: blue
        :return:
        """
        self.exp_dll.SetBoatColour(c_uint16(boat), c_uint16(r), c_uint16(g), c_uint16(b))

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
        self.exp_dll.SetMOB(c_double(lat), c_double(lon))

    def ping_mark(self, name: str, lat: float, lon: float, save: bool):
        """
        Ping a mark
        :param name: name of the mark
        :param lat: latitude
        :param lon: longitude
        :param save: save the mark
        :return:
        """
        self.exp_dll.PingMark(name.encode('utf-8'), c_double(lat), c_double(lon), c_bool(save))

    def create_active_route(self, name: str, save: bool = True):
        """
        Create an active route
        :param name: route name
        :param save: whether to save (default True)
        :return:
        """
        self.exp_dll.CreateActiveRoute(name.encode('utf-8'), c_bool(save))

    def add_mark_to_active_route(self, name: str, lat: float, lon: float, locked: bool = True, save: bool = True):
        """
        Add a mark to the active route
        :param name: mark name
        :param lat: latitude
        :param lon: longitude
        :param locked: locked (default True)
        :param save: whether to save (default True)
        :return:
        """
        self.exp_dll.AddMarkToActiveRoute(name.encode('utf-8'),
                                          c_double(lat), c_double(lon),
                                          c_bool(locked), c_bool(save))

    def get_variation(self, date: float, lat: float, lon: float) -> float:
        """
        Get the variation at a position
        :param date: date
        :param lat: latitude
        :param lon: longitude
        :return: variation
        """
        variation = c_double()
        self.exp_dll.GetVariation(c_double(date), c_double(lat), c_double(lon), ctypes.byref(variation))
        return variation.value

