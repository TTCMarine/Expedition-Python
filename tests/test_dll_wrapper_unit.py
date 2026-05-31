import ctypes
from unittest import TestCase
from unittest.mock import patch

from Expedition import ExpeditionDLL, Var


class FakeCFunction:
    def __init__(self, impl=None, return_value=None):
        self.impl = impl
        self.return_value = return_value
        self.argtypes = None
        self.restype = None
        self.calls = []

    def __call__(self, *args):
        self.calls.append(args)
        if self.impl is not None:
            return self.impl(*args)
        return self.return_value


def _to_int(value):
    return int(value.value) if hasattr(value, "value") else int(value)


class FakeExpDLL:
    def __init__(self):
        self.vars = {}
        self.var_precision = {}
        self.boat_names = {}
        self.boat_colours = {}
        self.ais_dangerous = True
        self.ais_name = "AIS TARGET"

        self.GetExpVarNum = FakeCFunction(return_value=606)
        self.GetExpVarName = FakeCFunction(impl=self._get_exp_var_name)
        self.SetExpUserVarName = FakeCFunction()
        self.SetVarPrecision = FakeCFunction(impl=self._set_var_precision)
        self.GetVarPrecision = FakeCFunction(impl=self._get_var_precision)
        self.SetExpVar = FakeCFunction(impl=self._set_exp_var)
        self.GetExpVar = FakeCFunction(impl=self._get_exp_var)
        self.SetExpVars = FakeCFunction(impl=self._set_exp_vars)
        self.GetExpVars = FakeCFunction(impl=self._get_exp_vars)
        self.GetSysVar = FakeCFunction(impl=self._get_sys_var)
        self.GetSysBool = FakeCFunction(impl=self._get_sys_bool)
        self.GetBoatNum = FakeCFunction(return_value=64)
        self.SetBoatName = FakeCFunction(impl=self._set_boat_name)
        self.GetBoatColour = FakeCFunction(impl=self._get_boat_colour)
        self.SetBoatColour = FakeCFunction(impl=self._set_boat_colour)
        self.GetVariation = FakeCFunction(impl=self._get_variation)
        self.GetAisDangerousCPA = FakeCFunction(impl=self._get_ais_dangerous_cpa)
        self.SetMOB = FakeCFunction()
        self.PingMark = FakeCFunction()
        self.CreateActiveRoute = FakeCFunction()
        self.AddMarkToActiveRoute = FakeCFunction()

    def _get_exp_var_name(self, var_id, name_buf):
        var_name = "User0" if _to_int(var_id) == int(Var.User0) else "Bsp"
        name_buf.value = var_name.encode("utf-8")

    def _set_var_precision(self, var_id, precision):
        self.var_precision[_to_int(var_id)] = _to_int(precision)

    def _get_var_precision(self, var_id, precision_out):
        precision_out._obj.value = self.var_precision.get(_to_int(var_id), 0)

    def _set_exp_var(self, var_id, value, boat):
        self.vars[(_to_int(var_id), _to_int(boat))] = float(value.value)

    def _get_exp_var(self, var_id, value_out, boat, id_alt_out):
        key = (_to_int(var_id), _to_int(boat))
        if key not in self.vars:
            return False
        value_out._obj.value = self.vars[key]
        id_alt_out._obj.value = _to_int(var_id)
        return True

    def _set_exp_vars(self, var_ids, values, n_vals, boat):
        count = _to_int(n_vals)
        boat_id = _to_int(boat)
        for index in range(count):
            self.vars[(int(var_ids[index]), boat_id)] = float(values[index])

    def _get_exp_vars(self, var_ids, values_out, n_vals, boat):
        count = _to_int(n_vals)
        boat_id = _to_int(boat)
        for index in range(count):
            key = (int(var_ids[index]), boat_id)
            if key not in self.vars:
                return False
            values_out[index] = self.vars[key]
        return True

    def _get_sys_var(self, var_id, value_out):
        value_out._obj.value = 12.5
        return True

    def _get_sys_bool(self, var_id, value_out):
        value_out._obj.value = True
        return True

    def _set_boat_name(self, boat, name):
        self.boat_names[_to_int(boat)] = name.decode("utf-8")

    def _set_boat_colour(self, boat, r, g, b):
        self.boat_colours[_to_int(boat)] = (_to_int(r), _to_int(g), _to_int(b))

    def _get_boat_colour(self, boat, r_out, g_out, b_out):
        r, g, b = self.boat_colours.get(_to_int(boat), (0, 0, 0))
        r_out._obj.value = r
        g_out._obj.value = g
        b_out._obj.value = b

    def _get_variation(self, utc, lat, lon, variation_out):
        variation_out._obj.value = 2.75
        return True

    def _get_ais_dangerous_cpa(self, dangerous_out, name_buf, name_len):
        dangerous_out._obj.value = self.ais_dangerous
        name_buf.value = self.ais_name


class TestDLLWrapperUnit(TestCase):
    def setUp(self):
        self.fake_dll = FakeExpDLL()
        self.windll = type("FakeWindll", (), {"LoadLibrary": lambda _, __: self.fake_dll})()
        with (
            patch("os.path.exists", return_value=True),
            patch.object(ctypes, "windll", self.windll, create=True),
        ):
            self.expedition = ExpeditionDLL("C:/fake")

    def test_ctypes_signatures_match_header(self):
        self.assertEqual(self.fake_dll.GetExpVarNum.argtypes, [])
        self.assertEqual(self.fake_dll.GetBoatNum.argtypes, [])
        self.assertEqual(
            self.fake_dll.GetAisDangerousCPA.argtypes,
            [ctypes.POINTER(ctypes.c_bool), ctypes.POINTER(ctypes.c_wchar), ctypes.c_uint16],
        )
        self.assertEqual(
            self.fake_dll.SetBoatColour.argtypes,
            [ctypes.c_uint16, ctypes.c_ubyte, ctypes.c_ubyte, ctypes.c_ubyte],
        )
        self.assertEqual(self.fake_dll.GetExpVarNum.restype, ctypes.c_int)
        self.assertEqual(self.fake_dll.GetBoatNum.restype, ctypes.c_int)

    def test_no_arg_count_functions_called_without_pointers(self):
        self.assertEqual(self.expedition.number_of_vars, 606)
        self.assertEqual(self.expedition.get_number_of_boats(), 64)
        self.assertEqual(len(self.fake_dll.GetExpVarNum.calls[0]), 0)
        self.assertEqual(len(self.fake_dll.GetBoatNum.calls[0]), 0)

    def test_precision_round_trip(self):
        self.expedition.set_var_precision(Var.User0, 3)
        precision = self.expedition.get_var_precision(Var.User0)
        self.assertEqual(precision, 3)

    def test_get_ais_dangerous_cpa_returns_expected_shape(self):
        dangerous, name = self.expedition.get_ais_dangerous_cpa()
        self.assertEqual((dangerous, name), (True, "AIS TARGET"))
        _, _, name_len = self.fake_dll.GetAisDangerousCPA.calls[-1]
        self.assertEqual(_to_int(name_len), 32)

    def test_set_and_get_var_value_uses_uint16_id_alt(self):
        self.expedition.set_exp_var_value(Var.Bsp, 9.7, boat=2)
        value = self.expedition.get_exp_var_value(Var.Bsp, boat=2)
        self.assertEqual(value, 9.7)

        # Fourth arg must be a uint16 out pointer (idAlt).
        get_call = self.fake_dll.GetExpVar.calls[-1]
        self.assertIsInstance(get_call[3]._obj, ctypes.c_uint16)

    def test_set_and_get_boat_colour_uses_ubyte_channels(self):
        self.expedition.set_boat_colour(1, 1, 2, 255)
        self.assertEqual(self.expedition.get_boat_colour(1), (1, 2, 255))

    def test_boat_name_length_validation(self):
        with self.assertRaises(ValueError):
            self.expedition.set_boat_name(1, "x" * 33)
