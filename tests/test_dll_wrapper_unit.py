import ctypes
from unittest import TestCase
from unittest.mock import patch

from Expedition import ExpeditionAPIError, ExpeditionDLL, ExVal, Var
from Expedition.exval import ExValStruct


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


class _FakeExpDLLBase:
    def __init__(self):
        self.vars = {}
        self.ex_vals = {}
        self.var_precision = {}
        self.boat_names = {}
        self.boat_colours = {}
        self.ais_dangerous = True
        self.ais_name = "AIS TARGET"

        self.GetExpVarNum = FakeCFunction(return_value=606)
        self.GetExpVarName = FakeCFunction(impl=self._get_exp_var_name)
        self.SetExpUserVarName = FakeCFunction()
        self.SetExpVar = FakeCFunction(impl=self._set_exp_var)
        self.GetExpVar = FakeCFunction(impl=self._get_exp_var)
        self.GetSysVar = FakeCFunction(impl=self._get_sys_var)
        self.GetSysBool = FakeCFunction(impl=self._get_sys_bool)
        self.GetBoatNum = FakeCFunction(return_value=64)
        self.SetMOB = FakeCFunction()

    def _get_exp_var_name(self, var_id, name_buf):
        var_name = "User0" if _to_int(var_id) == int(Var.User0) else "Bsp"
        name_buf.value = var_name.encode("utf-8")

    def _set_exp_var(self, var_id, value, boat):
        key = (_to_int(var_id), _to_int(boat))
        self.vars[key] = float(value.value)
        if key in self.ex_vals:
            self.ex_vals[key] = ExVal(value=self.vars[key], time=self.ex_vals[key].time)

    def _get_exp_var(self, var_id, value_out, boat, id_alt_out):
        key = (_to_int(var_id), _to_int(boat))
        if key not in self.vars:
            return False
        value_out._obj.value = self.vars[key]
        id_alt_out._obj.value = _to_int(var_id)
        return True

    def _get_sys_var(self, var_id, value_out):
        value_out._obj.value = 12.5
        return True

    def _get_sys_bool(self, var_id, value_out):
        value_out._obj.value = True
        return True


class FakeLegacyExpDLL(_FakeExpDLLBase):
    def __init__(self):
        super().__init__()
        self.SetVarPrecision = FakeCFunction(impl=self._set_var_precision)
        self.GetVarPrecision = FakeCFunction(impl=self._get_var_precision)
        self.SetExpVars = FakeCFunction(impl=self._set_exp_vars)
        self.GetExpVars = FakeCFunction(impl=self._get_exp_vars)
        self.SetBoatName = FakeCFunction(impl=self._set_boat_name)
        self.GetBoatColour = FakeCFunction(impl=self._get_boat_colour)
        self.SetBoatColour = FakeCFunction(impl=self._set_boat_colour)
        self.GetVariation = FakeCFunction(impl=self._get_variation)
        self.GetAisDangerousCPA = FakeCFunction(impl=self._get_ais_dangerous_cpa)
        self.PingMark = FakeCFunction()
        self.CreateActiveRoute = FakeCFunction()
        self.AddMarkToActiveRoute = FakeCFunction()

    def _set_var_precision(self, var_id, precision):
        self.var_precision[_to_int(var_id)] = _to_int(precision)

    def _get_var_precision(self, var_id, precision_out):
        precision_out._obj.value = self.var_precision.get(_to_int(var_id), 0)

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


class FakeV12ExpDLL(_FakeExpDLLBase):
    def __init__(self):
        super().__init__()
        self.SetExpVar2 = FakeCFunction(impl=self._set_exp_var2)
        self.GetExpVar2 = FakeCFunction(impl=self._get_exp_var2)

    def _set_exp_var2(self, var_id, value, boat):
        key = (_to_int(var_id), _to_int(boat))
        if isinstance(value, ExValStruct):
            ex_val = ExVal.from_struct(value)
        else:
            ex_val = ExVal(value=float(value.value), time=int(value.time))
        self.ex_vals[key] = ex_val
        self.vars[key] = ex_val.value

    def _get_exp_var2(self, var_id, value_out, boat, id_alt_out):
        key = (_to_int(var_id), _to_int(boat))
        if key not in self.ex_vals:
            return False
        value_out._obj.time = self.ex_vals[key].time
        value_out._obj.value = self.ex_vals[key].value
        id_alt_out._obj.value = _to_int(var_id)
        return True


def _make_expedition(fake_dll):
    windll = type("FakeWindll", (), {"LoadLibrary": lambda _, __: fake_dll})()
    with (
        patch("os.path.exists", return_value=True),
        patch.object(ctypes, "windll", windll, create=True),
    ):
        return ExpeditionDLL("C:/fake")


class TestDLLWrapperLegacy(TestCase):
    def setUp(self):
        self.fake_dll = FakeLegacyExpDLL()
        self.expedition = _make_expedition(self.fake_dll)

    def test_api_version_is_legacy(self):
        self.assertEqual(self.expedition.api_version, "legacy")
        self.assertTrue(self.expedition.has_batch_vars)
        self.assertFalse(self.expedition.has_exp_var2)

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

        get_call = self.fake_dll.GetExpVar.calls[-1]
        self.assertIsInstance(get_call[3]._obj, ctypes.c_uint16)

    def test_set_and_get_boat_colour_uses_ubyte_channels(self):
        self.expedition.set_boat_colour(1, 1, 2, 255)
        self.assertEqual(self.expedition.get_boat_colour(1), (1, 2, 255))

    def test_boat_name_length_validation(self):
        with self.assertRaises(ValueError):
            self.expedition.set_boat_name(1, "x" * 33)

    def test_batch_vars_use_dll_exports(self):
        self.expedition.set_exp_vars([Var.User0, Var.User1], [1.0, 2.0])
        self.assertEqual(len(self.fake_dll.SetExpVars.calls), 1)
        self.assertEqual(len(self.fake_dll.SetExpVar.calls), 0)


class TestDLLWrapperV12(TestCase):
    def setUp(self):
        self.fake_dll = FakeV12ExpDLL()
        self.expedition = _make_expedition(self.fake_dll)

    def test_api_version_is_1_2(self):
        self.assertEqual(self.expedition.api_version, "1.2")
        self.assertFalse(self.expedition.has_batch_vars)
        self.assertTrue(self.expedition.has_exp_var2)

    def test_batch_vars_fallback_to_single_exports(self):
        self.expedition.set_exp_vars([Var.User0, Var.User1, Var.User2], [0, 1, 2])
        self.assertEqual(len(self.fake_dll.SetExpVar.calls), 3)
        values = self.expedition.get_exp_vars([Var.User0, Var.User1, Var.User2])
        self.assertEqual(values, [0, 1, 2])
        self.assertEqual(len(self.fake_dll.GetExpVar.calls), 3)

    def test_boat_position_uses_single_var_fallback(self):
        self.expedition.set_boat_position(1, (50.8, -1.3))
        position = self.expedition.get_boat_position(1)
        self.assertEqual(position, (50.8, -1.3))

    def test_removed_apis_raise_expedition_api_error(self):
        for method, args in (
            (self.expedition.set_var_precision, (Var.User0, 3)),
            (self.expedition.get_var_precision, (Var.User0,)),
            (self.expedition.set_boat_name, (1, "boat")),
            (self.expedition.get_boat_colour, (1,)),
            (self.expedition.set_boat_colour, (1, 0, 0, 0)),
            (self.expedition.get_ais_dangerous_cpa, ()),
            (self.expedition.ping_mark, ("mark", 1.0, 2.0, False)),
            (self.expedition.create_active_route, ("route",)),
            (self.expedition.add_mark_to_active_route, ("mark", 1.0, 2.0)),
        ):
            with self.subTest(method=method.__name__):
                with self.assertRaises(ExpeditionAPIError):
                    method(*args)

    def test_exp_var2_round_trip(self):
        self.expedition.set_exp_var2(Var.User0, ExVal(value=12.5, time=99))
        result = self.expedition.get_exp_var2(Var.User0)
        self.assertEqual(result, ExVal(value=12.5, time=99))
        self.assertEqual(len(self.fake_dll.SetExpVar2.calls), 1)
        self.assertEqual(len(self.fake_dll.GetExpVar2.calls), 1)

    def test_get_variation_uses_magvar_fallback(self):
        self.expedition.set_exp_var_value(Var.MagVar, 3.25, boat=2)
        variation = self.expedition.get_variation(50.8, -1.3)
        self.assertEqual(variation, 3.25)
