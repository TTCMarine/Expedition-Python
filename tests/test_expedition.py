"""Integration tests against a running Expedition.

These tests load the real ExpDLL.dll and need Expedition to be running. They skip
(rather than fail) on other platforms, when no DLL folder can be found, or when
Expedition is not running.

Select the build under test with the EXPEDITION_DLL_DIR environment variable, for example
``set EXPEDITION_DLL_DIR=C:\\Program Files\\Expedition\\ExpeditionX64``. Without it the
registry location is used. The Python interpreter must match the build's architecture.
"""

import os
import sys
import unittest

from Expedition import (
    ExpeditionAPIError,
    ExpeditionDLL,
    ExpeditionLoadError,
    SysVar,
    Var,
)

IS_WINDOWS = sys.platform == "win32"
EXPEDITION_DLL_DIR = os.environ.get("EXPEDITION_DLL_DIR")


def _open_expedition():
    """Return a connected ExpeditionDLL, or a string explaining why it is unavailable."""
    if not IS_WINDOWS:
        return "Integration tests require Windows with Expedition installed"
    try:
        if EXPEDITION_DLL_DIR:
            expedition = ExpeditionDLL(EXPEDITION_DLL_DIR)
        else:
            expedition = ExpeditionDLL.from_default_location()
    except (FileNotFoundError, ExpeditionLoadError, ExpeditionAPIError) as exc:
        return f"Expedition DLL not available: {exc}"
    if not expedition.is_running():
        return "Expedition is not running"
    return expedition


_OPEN_RESULT = _open_expedition()
_SKIP_REASON = _OPEN_RESULT if isinstance(_OPEN_RESULT, str) else None


@unittest.skipIf(_SKIP_REASON is not None, _SKIP_REASON or "")
class TestExpedition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expedition = _OPEN_RESULT

    def test_number_of_vars(self):
        self.assertEqual(self.expedition.number_of_vars, int(Var.NumChannels))

    def test_get_exp_var_name(self):
        for var in (Var.Bsp, Var.Lat, Var.Lon, Var.Awa, Var.Aws):
            with self.subTest(var=var.name):
                var_name = self.expedition.get_exp_var_name(var)
                self.assertIsInstance(var_name, str)
                self.assertGreater(len(var_name), 0)

    def test_set_and_get_exp_var_value(self):
        self.expedition.set_exp_var_value(Var.Bsp, 10.4)
        self.assertEqual(self.expedition.get_exp_var_value(Var.Bsp), 10.4)

    def test_set_and_get_exp_user_var_name(self):
        self.expedition.set_exp_user_var_name(Var.User0, "User Var 0")
        self.assertEqual("User Var 0", self.expedition.get_exp_var_name(Var.User0))

    def test_set_and_get_exp_vars(self):
        self.expedition.set_exp_vars([Var.User0, Var.User1, Var.User2], [0, 1, 2])
        values = self.expedition.get_exp_vars([Var.User0, Var.User1, Var.User2])
        self.assertEqual(values, [0, 1, 2])

    def test_get_sys_var(self):
        boat_length = self.expedition.get_sys_var(SysVar.BoatLength)
        if boat_length is not None:
            self.assertIsInstance(boat_length, float)

    def test_set_and_get_boat_position(self):
        self.expedition.set_boat_position(1, (50.8, -1.3))
        self.assertEqual(self.expedition.get_boat_position(1), (50.8, -1.3))

    def test_set_by_name(self):
        self.expedition.set_exp_var_by_name("Lat", 50.7, 1)
        self.assertEqual(self.expedition.get_exp_var_value(Var.Lat, 1), 50.7)

    def test_set_by_name_error(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_by_name("Invalid", 50.7)

    def test_get_by_name(self):
        self.expedition.set_exp_var_value(Var.Lon, -1.3, 1)
        self.assertEqual(self.expedition.get_exp_var_value_by_name("Lon", 1), -1.3)

    def test_set_dict(self):
        self.expedition.set_exp_vars_dict({Var.Lat: 50.8, Var.Lon: -1.4}, 1)
        self.assertEqual(self.expedition.get_exp_var_value(Var.Lat, 1), 50.8)
        self.assertEqual(self.expedition.get_exp_var_value(Var.Lon, 1), -1.4)

    def test_get_exp_var_ex_reports_resolved_channel(self):
        self.expedition.set_exp_var_value(Var.Bsp, 8.0, 1)
        reading = self.expedition.get_exp_var_ex(Var.Bsp, 1)
        self.assertIsNotNone(reading)
        self.assertEqual(reading.value, 8.0)

    def test_get_variation(self):
        variation = self.expedition.get_variation(50.8, -1.3)
        if variation is not None:
            self.assertIsInstance(variation, float)

    @unittest.skipUnless(IS_WINDOWS, "Requires Windows")
    def test_set_and_get_boat_colour(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("GetBoatColour not exported on ExpDLL API 1.2")
        self.expedition.set_boat_colour(0, 0, 0, 0)
        self.assertEqual(self.expedition.get_boat_colour(0), (0, 0, 0))

    def test_set_and_get_var_precision(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("SetVarPrecision not exported on ExpDLL API 1.2")
        self.expedition.set_var_precision(Var.User0, 3)
        self.assertEqual(self.expedition.get_var_precision(Var.User0), 3)

    def test_get_ais_dangerous_cpa_shape(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("GetAisDangerousCPA not exported on ExpDLL API 1.2")
        dangerous, name = self.expedition.get_ais_dangerous_cpa()
        self.assertIsInstance(dangerous, bool)
        self.assertIsInstance(name, str)

    def test_exp_var2_on_v12_dll(self):
        if not self.expedition.has_exp_var2:
            self.skipTest("SetExpVar2 not exported on this ExpDLL")
        from Expedition import ExVal

        self.expedition.set_exp_var2(Var.User0, ExVal.from_double(7.5))
        result = self.expedition.get_exp_var2(Var.User0)
        self.assertIsNotNone(result)
        self.assertEqual(result.as_double(), 7.5)

    def test_legacy_only_api_raises_on_v12(self):
        if self.expedition.api_version == "legacy":
            self.skipTest("Legacy-only error checks require ExpDLL API 1.2")
        with self.assertRaises(ExpeditionAPIError):
            self.expedition.set_var_precision(Var.User0, 3)


if __name__ == "__main__":
    unittest.main()
