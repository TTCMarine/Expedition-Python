import ctypes
import sys
import warnings
from datetime import datetime, timezone
from unittest import TestCase
from unittest.mock import patch

from Expedition import (
    ExpeditionAPIError,
    ExpeditionDLL,
    ExpeditionLoadError,
    ExpeditionNotRunningError,
    ExpeditionVersionWarning,
    ExpeditionWriteError,
    ExpeditionWriteWarning,
    ExVal,
    SysBooleanVar,
    SysVar,
    ValType,
    Var,
    _loader,
)
from Expedition.dll_wrapper import GPS_BOAT0_CHANNELS
from Expedition.exval import ExValStruct, datetime_to_winrt_ticks, winrt_ticks_to_datetime

FAKE_CHANNELS = 418
FAKE_BOATS = 100
FAKE_INVALID = 32767.0


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
    """Models the parts of ExpDLL that the wrapper relies on.

    - Writes to ID 0 (Utc) are ignored.
    - Writes are ignored while Expedition is not running (``running = False``).
    - Boat 0 GPS channels are ignored unless ``gps_from_dll`` is True.
    - GetExpVar on Utc with Expedition closed returns the invalid sentinel.
    """

    def __init__(self):
        self.vars = {}
        self.ex_vals = {}
        self.var_precision = {}
        self.boat_names = {}
        self.boat_colours = {}
        self.ais_dangerous = True
        self.ais_name = "AIS TARGET"
        self.running = True
        self.gps_from_dll = False
        self.utc = 45000.5
        self.alt_map = {}

        self.GetExpVarNum = FakeCFunction(return_value=FAKE_CHANNELS)
        self.GetExpVarName = FakeCFunction(impl=self._get_exp_var_name)
        self.SetExpUserVarName = FakeCFunction()
        self.SetExpVar = FakeCFunction(impl=self._set_exp_var)
        self.GetExpVar = FakeCFunction(impl=self._get_exp_var)
        self.GetSysVar = FakeCFunction(impl=self._get_sys_var)
        self.GetSysBool = FakeCFunction(impl=self._get_sys_bool)
        self.GetBoatNum = FakeCFunction(return_value=FAKE_BOATS)
        self.SetMOB = FakeCFunction()

    def _get_exp_var_name(self, var_id, name_buf):
        var_name = "User0" if _to_int(var_id) == int(Var.User0) else "Bsp"
        name_buf.value = var_name.encode("utf-8")

    def _is_dropped(self, var_id, boat_id):
        if var_id == int(Var.Utc) or not self.running:
            return True
        return boat_id == 0 and not self.gps_from_dll and var_id in GPS_BOAT0_CHANNELS

    def _set_exp_var(self, var_id, value, boat):
        key = (_to_int(var_id), _to_int(boat))
        if self._is_dropped(*key):
            return
        self.vars[key] = float(value.value)

    def _get_exp_var(self, var_id, value_out, boat, id_alt_out):
        var = _to_int(var_id)
        boat_id = _to_int(boat)
        if var == int(Var.Utc) and boat_id == 0:
            value_out._obj.value = self.utc if self.running else FAKE_INVALID
            id_alt_out._obj.value = var
            return True
        resolved = self.alt_map.get(var, var)
        key = (resolved, boat_id)
        if key not in self.vars:
            return False
        value_out._obj.value = self.vars[key]
        id_alt_out._obj.value = resolved
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
            self._set_exp_var(
                ctypes.c_uint16(var_ids[index]), ctypes.c_double(values[index]), boat_id
            )

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
        ex_val = ExVal.from_struct(value)
        if self._is_dropped(*key):
            return
        self.ex_vals[key] = ex_val
        if ex_val.type is ValType.Double:
            self.vars[key] = ex_val.as_double()

    def _get_exp_var2(self, var_id, value_out, boat, id_alt_out):
        key = (_to_int(var_id), _to_int(boat))
        if key not in self.ex_vals:
            return False
        stored = self.ex_vals[key].to_struct()
        dest = value_out._obj
        dest.type = stored.type
        dest.u = stored.u
        id_alt_out._obj.value = _to_int(var_id)
        return True


def _make_expedition(fake_dll, strict=False):
    windll = type("FakeWindll", (), {"LoadLibrary": lambda _, __: fake_dll})()
    with (
        patch("os.path.exists", return_value=True),
        patch.object(ctypes, "windll", windll, create=True),
        patch.object(_loader, "preflight", return_value="AMD64"),
    ):
        return ExpeditionDLL("C:/fake", strict=strict)


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

    def test_counts_read_once_at_load(self):
        self.assertEqual(self.expedition.number_of_vars, FAKE_CHANNELS)
        self.assertEqual(self.expedition.get_number_of_boats(), FAKE_BOATS)
        self.assertEqual(len(self.fake_dll.GetExpVarNum.calls), 1)
        self.assertEqual(len(self.fake_dll.GetBoatNum.calls), 1)
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
        self.expedition.set_exp_var2(Var.User0, ExVal.from_double(12.5))
        result = self.expedition.get_exp_var2(Var.User0)
        self.assertEqual(result, ExVal.from_double(12.5))
        self.assertEqual(len(self.fake_dll.SetExpVar2.calls), 1)
        self.assertEqual(len(self.fake_dll.GetExpVar2.calls), 1)

    def test_exval_struct_size(self):
        self.assertEqual(ctypes.sizeof(ExValStruct), 16)

    def test_winrt_datetime_round_trip(self):
        dt = datetime(2024, 6, 15, 12, 30, 0, tzinfo=timezone.utc)
        ticks = datetime_to_winrt_ticks(dt)
        restored = winrt_ticks_to_datetime(ticks)
        self.assertEqual(restored, dt)

    def test_exp_var2_int64_round_trip(self):
        ticks = datetime_to_winrt_ticks(datetime(2024, 1, 1, tzinfo=timezone.utc))
        self.expedition.set_exp_var2(Var.User1, ExVal.from_ticks(ticks))
        result = self.expedition.get_exp_var2(Var.User1)
        self.assertEqual(result, ExVal.from_ticks(ticks))

    def test_get_variation_uses_magvar_fallback(self):
        self.expedition.set_exp_var_value(Var.MagVar, 3.25, boat=2)
        variation = self.expedition.get_variation(50.8, -1.3)
        self.assertEqual(variation, 3.25)


class TestKnownIds(TestCase):
    def test_channel_ids_match_headers(self):
        self.assertEqual(int(Var.NumChannels), 418)
        self.assertEqual(int(Var.BowLat), 414)
        self.assertEqual(int(Var.SysGpsTimeDelta), 256)
        self.assertEqual(int(SysVar.CalTwa), 57)
        self.assertEqual(int(SysVar.NumSysChannels), 76)
        self.assertEqual(int(SysBooleanVar.AutoPan), 0)
        self.assertEqual(int(SysBooleanVar.Max), 60)

    def test_user_variables_are_172_to_203(self):
        self.assertEqual(int(Var.User0), 172)
        self.assertEqual(int(Var.User31), 203)
        self.assertEqual(int(Var.UserMax), 203)


class TestValidation(TestCase):
    def setUp(self):
        self.fake_dll = FakeLegacyExpDLL()
        self.expedition = _make_expedition(self.fake_dll)

    def test_write_to_utc_is_rejected(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_value(Var.Utc, 1.0)
        self.assertEqual(len(self.fake_dll.SetExpVar.calls), 0)

    def test_read_of_utc_is_allowed(self):
        self.assertEqual(self.expedition.get_exp_var_value(Var.Utc), 45000.5)

    def test_channel_out_of_range_is_rejected(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_value(FAKE_CHANNELS, 1.0)
        with self.assertRaises(ValueError):
            self.expedition.get_exp_var_value(FAKE_CHANNELS)
        with self.assertRaises(ValueError):
            self.expedition.get_exp_var_value(-1)

    def test_boat_out_of_range_is_rejected(self):
        for boat in (-1, FAKE_BOATS, 65535, True, 1.5):
            with self.subTest(boat=boat):
                with self.assertRaises(ValueError):
                    self.expedition.set_exp_var_value(Var.Bsp, 1.0, boat=boat)
                with self.assertRaises(ValueError):
                    self.expedition.get_exp_var_value(Var.Bsp, boat=boat)
        self.assertEqual(len(self.fake_dll.SetExpVar.calls), 0)

    def test_batch_validates_every_channel_before_writing(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_vars([Var.Bsp, Var.Utc], [1.0, 2.0])
        self.assertEqual(len(self.fake_dll.SetExpVars.calls), 0)

    def test_by_name_errors_are_value_errors(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_by_name("NoSuchChannel", 1.0)
        with self.assertRaises(ValueError):
            self.expedition.get_exp_var_value_by_name("NoSuchChannel")

    def test_by_name_round_trip(self):
        self.expedition.set_exp_var_by_name("Bsp", 6.5, boat=1)
        self.assertEqual(self.expedition.get_exp_var_value_by_name("Bsp", boat=1), 6.5)

    def test_sys_var_ids_are_range_checked(self):
        self.assertEqual(self.expedition.get_sys_var(SysVar.CalTwa), 12.5)
        with self.assertRaises(ValueError):
            self.expedition.get_sys_var(76)
        with self.assertRaises(ValueError):
            self.expedition.get_sys_var(-1)

    def test_sys_bool_ids_are_range_checked(self):
        self.assertTrue(self.expedition.get_sys_bool(SysBooleanVar.AutoPan))
        with self.assertRaises(ValueError):
            self.expedition.get_sys_bool(60)

    def test_user_var_name_accepts_user_members_and_indices(self):
        self.expedition.set_exp_user_var_name(Var.User0, "Speed")
        self.expedition.set_exp_user_var_name(0, "Speed")
        self.expedition.set_exp_user_var_name(31, "Speed")
        self.assertEqual(len(self.fake_dll.SetExpUserVarName.calls), 3)

    def test_user_var_name_rejects_non_user_channel_members(self):
        # Var.Bsp has value 1, which the DLL would map to User1 and rename.
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(Var.Bsp, "Speed")
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(Var.UserMax + 1, "Speed")
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(32, "Speed")
        self.assertEqual(len(self.fake_dll.SetExpUserVarName.calls), 0)

    def test_user_var_name_limit_is_15_bytes(self):
        self.expedition.set_exp_user_var_name(Var.User0, "x" * 15)
        self.assertEqual(self.fake_dll.SetExpUserVarName.calls[-1][1], b"x" * 15)
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(Var.User0, "x" * 16)

    def test_user_var_name_must_be_str(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(Var.User0, 123)

    def test_var_precision_uses_same_user_rule(self):
        with self.assertRaises(ValueError):
            self.expedition.set_var_precision(Var.Bsp, 2)
        with self.assertRaises(ValueError):
            self.expedition.get_var_precision(Var.Bsp)

    def test_boat_colour_components_are_range_checked(self):
        with self.assertRaises(ValueError):
            self.expedition.set_boat_colour(1, 256, 0, 0)
        with self.assertRaises(ValueError):
            self.expedition.set_boat_colour(1, 0, -1, 0)

    def test_name_lookup_by_var_name_still_works(self):
        self.assertEqual(self.expedition.get_exp_var_name(Var.User0), "User0")

    def test_multibyte_name_rejected_on_non_windows(self):
        import sys

        if sys.platform == "win32":
            self.skipTest("ANSI code page accepts this name on Windows")
        with self.assertRaises(ValueError):
            self.expedition.set_exp_user_var_name(Var.User0, "caf\u00e9")


class TestGpsBoat0Warning(TestCase):
    def setUp(self):
        self.fake_dll = FakeLegacyExpDLL()
        self.expedition = _make_expedition(self.fake_dll)

    def test_gps_channel_on_boat0_warns(self):
        with self.assertWarns(ExpeditionWriteWarning):
            self.expedition.set_exp_var_value(Var.Lat, 50.0, boat=0)

    def test_gps_channel_on_other_boat_does_not_warn(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.expedition.set_exp_var_value(Var.Lat, 50.0, boat=1)
        self.assertFalse([w for w in caught if issubclass(w.category, ExpeditionWriteWarning)])

    def test_non_gps_channel_on_boat0_does_not_warn(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            self.expedition.set_exp_var_value(Var.Bsp, 5.0, boat=0)
        self.assertFalse([w for w in caught if issubclass(w.category, ExpeditionWriteWarning)])

    def test_gps_channels_list_is_expected(self):
        self.assertIn(Var.Lat, GPS_BOAT0_CHANNELS)
        self.assertIn(Var.GpsTime, GPS_BOAT0_CHANNELS)
        self.assertNotIn(Var.Bsp, GPS_BOAT0_CHANNELS)

    def test_gps_write_still_reaches_dll_when_not_strict(self):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.expedition.set_exp_var_value(Var.Lat, 50.0, boat=0)
        self.assertEqual(len(self.fake_dll.SetExpVar.calls), 1)


class TestVersionDriftWarning(TestCase):
    def test_mismatched_channel_count_warns(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.GetExpVarNum.return_value = 606
        with self.assertWarns(ExpeditionVersionWarning):
            _make_expedition(fake_dll)

    def test_matching_channel_count_does_not_warn(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            _make_expedition(FakeLegacyExpDLL())
        self.assertFalse([w for w in caught if issubclass(w.category, ExpeditionVersionWarning)])


class TestIsRunning(TestCase):
    def test_running_when_utc_is_valid(self):
        expedition = _make_expedition(FakeLegacyExpDLL())
        self.assertTrue(expedition.is_running())

    def test_not_running_when_utc_is_sentinel(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.running = False
        expedition = _make_expedition(fake_dll)
        self.assertFalse(expedition.is_running())


class TestStrictMode(TestCase):
    def test_default_mode_is_silent_when_not_running(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.running = False
        expedition = _make_expedition(fake_dll)
        expedition.set_exp_var_value(Var.Bsp, 4.0, boat=1)
        self.assertIsNone(expedition.get_exp_var_value(Var.Bsp, boat=1))
        self.assertFalse(expedition.strict)

    def test_strict_raises_when_not_running(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.running = False
        expedition = _make_expedition(fake_dll, strict=True)
        with self.assertRaises(ExpeditionNotRunningError):
            expedition.set_exp_var_value(Var.Bsp, 4.0, boat=1)
        with self.assertRaises(ExpeditionNotRunningError):
            expedition.set_exp_vars([Var.Bsp], [4.0], boat=1)
        self.assertEqual(len(fake_dll.SetExpVar.calls), 0)

    def test_strict_write_that_applies_returns_silently(self):
        expedition = _make_expedition(FakeLegacyExpDLL(), strict=True)
        expedition.set_exp_var_value(Var.Bsp, 4.0, boat=1)
        self.assertEqual(expedition.get_exp_var_value(Var.Bsp, boat=1), 4.0)

    def test_strict_batch_write_reads_back_every_value(self):
        expedition = _make_expedition(FakeLegacyExpDLL(), strict=True)
        expedition.set_exp_vars([Var.Bsp, Var.Awa], [4.0, 30.0], boat=1)
        self.assertEqual(expedition.get_exp_vars([Var.Bsp, Var.Awa], boat=1), [4.0, 30.0])

    def test_strict_detects_dropped_gps_write_on_boat0(self):
        expedition = _make_expedition(FakeLegacyExpDLL(), strict=True)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            with self.assertRaises(ExpeditionWriteError):
                expedition.set_exp_var_value(Var.Lat, 50.0, boat=0)

    def test_non_strict_gps_write_on_boat0_is_silent_drop(self):
        fake_dll = FakeLegacyExpDLL()
        expedition = _make_expedition(fake_dll)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            expedition.set_exp_var_value(Var.Lat, 50.0, boat=0)
        self.assertIsNone(expedition.get_exp_var_value(Var.Lat, boat=0))

    def test_strict_set_boat_position_on_scratch_boat(self):
        expedition = _make_expedition(FakeLegacyExpDLL(), strict=True)
        expedition.set_boat_position(2, (50.8, -1.3))
        self.assertEqual(expedition.get_boat_position(2), (50.8, -1.3))

    def test_strict_skips_readback_for_alternating_channels(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.alt_map[int(Var.Alt0)] = int(Var.Bsp)
        expedition = _make_expedition(fake_dll, strict=True)
        # The write is stored against Alt0's slot, so Bsp is never set; no error expected.
        expedition.set_exp_var_value(Var.Alt0, 7.0, boat=1)


class TestExpVarEx(TestCase):
    def test_returns_value_and_resolved_channel(self):
        fake_dll = FakeLegacyExpDLL()
        fake_dll.alt_map[int(Var.Alt0)] = int(Var.Bsp)
        expedition = _make_expedition(fake_dll)
        expedition.set_exp_var_value(Var.Bsp, 8.25, boat=1)

        reading = expedition.get_exp_var_ex(Var.Alt0, boat=1)

        self.assertEqual(reading.value, 8.25)
        self.assertEqual(reading.resolved_var, Var.Bsp)

    def test_resolved_channel_matches_request_for_plain_channels(self):
        expedition = _make_expedition(FakeLegacyExpDLL())
        expedition.set_exp_var_value(Var.Awa, 30.0, boat=1)
        reading = expedition.get_exp_var_ex(Var.Awa, boat=1)
        self.assertEqual(reading.resolved_var, Var.Awa)

    def test_returns_none_when_no_value(self):
        expedition = _make_expedition(FakeLegacyExpDLL())
        self.assertIsNone(expedition.get_exp_var_ex(Var.Awa, boat=1))

    def test_get_exp_var_value_keeps_returning_plain_float(self):
        expedition = _make_expedition(FakeLegacyExpDLL())
        expedition.set_exp_var_value(Var.Awa, 30.0, boat=1)
        self.assertEqual(expedition.get_exp_var_value(Var.Awa, boat=1), 30.0)


def _failing_windll(error):
    def load_library(_, __):
        raise error

    return type("FakeWindll", (), {"LoadLibrary": load_library})()


class TestLoadErrors(TestCase):
    def test_winerror_126_names_companion_library(self):
        error = OSError("The specified module could not be found")
        error.winerror = 126
        windll = _failing_windll(error)
        with patch.object(ctypes, "windll", windll, create=True):
            with self.assertRaises(_loader.ExpeditionLoadError) as caught:
                _loader.load_dll("C:/fake/ExpDLL.dll", "ARM64")
        message = str(caught.exception)
        self.assertIn("libcrypto-3-arm64.dll", message)
        self.assertIn("mfc140u.dll", message)

    def test_amd64_companion_named_for_x64_build(self):
        error = OSError("missing")
        error.winerror = 126
        windll = _failing_windll(error)
        with patch.object(ctypes, "windll", windll, create=True):
            with self.assertRaises(_loader.ExpeditionLoadError) as caught:
                _loader.load_dll("C:/fake/ExpDLL.dll", "AMD64")
        self.assertIn("libcrypto-3-x64.dll", str(caught.exception))

    def test_other_load_failures_are_wrapped(self):
        error = OSError("access denied")
        error.winerror = 5
        windll = _failing_windll(error)
        with patch.object(ctypes, "windll", windll, create=True):
            with self.assertRaises(_loader.ExpeditionLoadError):
                _loader.load_dll("C:/fake/ExpDLL.dll", "AMD64")

    def test_non_windows_load_is_clear_error(self):
        with patch.object(ctypes, "windll", None, create=True):
            with self.assertRaises(_loader.ExpeditionLoadError):
                _loader.load_dll("C:/fake/ExpDLL.dll", "AMD64")

    def test_registry_lookup_errors_are_load_errors(self):
        from Expedition import dll_wrapper

        with patch.object(sys, "platform", "darwin"):
            with self.assertRaises(ExpeditionLoadError):
                dll_wrapper.get_expedition_location()
