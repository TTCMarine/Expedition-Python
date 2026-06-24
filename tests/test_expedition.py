import os
import sys
import unittest

from Expedition import ExpeditionAPIError, ExpeditionDLL, SysVar, Var

EXPEDITION_INSTALL_64_PATH = "C:\\Program Files\\Expedition\\Expedition"
EXPEDITION_INSTALL_32_PATH = "C:\\Program Files (x86)\\Expedition\\Expedition"
EXPEDITION_X_PATH = "C:\\Program Files\\Expedition\\ExpeditionX"

# Check if we're on Windows and if Expedition DLL is available
IS_WINDOWS = sys.platform == "win32"
DLL_AVAILABLE = False

if IS_WINDOWS:
    for path in [EXPEDITION_X_PATH, EXPEDITION_INSTALL_64_PATH, EXPEDITION_INSTALL_32_PATH]:
        dll_path = os.path.join(path, "ExpDLL.dll")
        if os.path.exists(dll_path):
            DLL_AVAILABLE = True
            break
    if not DLL_AVAILABLE:
        try:
            exp = ExpeditionDLL.from_default_location()
            DLL_AVAILABLE = True
            del exp
        except Exception:
            pass


class TestExpedition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up the expedition instance once for all tests."""
        cls.expedition = None
        cls.skip_reason = None

        if not IS_WINDOWS:
            cls.skip_reason = "Tests require Windows with Expedition DLL installed"
        elif not DLL_AVAILABLE:
            cls.skip_reason = (
                "Expedition DLL not found. Install Expedition or set up mock implementation."
            )
        else:
            try:
                cls.expedition = ExpeditionDLL.from_default_location()
            except (FileNotFoundError, OSError, ImportError):
                for path in (
                    EXPEDITION_X_PATH,
                    EXPEDITION_INSTALL_64_PATH,
                    EXPEDITION_INSTALL_32_PATH,
                ):
                    try:
                        cls.expedition = ExpeditionDLL(path)
                        break
                    except (FileNotFoundError, OSError):
                        continue
                if cls.expedition is None:
                    cls.skip_reason = "Could not initialize ExpeditionDLL"

    def setUp(self):
        """Skip tests if expedition instance is not available."""
        if self.skip_reason:
            self.skipTest(self.skip_reason)
        if self.expedition is None:
            self.skipTest("ExpeditionDLL instance not available")

    def test_number_of_vars(self):
        no_of_channels = self.expedition.number_of_vars
        self.assertIsInstance(no_of_channels, int)
        if DLL_AVAILABLE and IS_WINDOWS:
            self.assertEqual(no_of_channels, Var.NumChannels)

    def test_get_exp_var_name(self):
        test_vars = [Var.Bsp, Var.Lat, Var.Lon, Var.Awa, Var.Aws]
        for var in test_vars:
            var_name = self.expedition.get_exp_var_name(var)
            self.assertIsInstance(var_name, str)
            self.assertGreater(len(var_name), 0)

    def test_set_and_get_exp_var_value(self):
        self.expedition.set_exp_var_value(Var.Bsp, 10.4)
        value = self.expedition.get_exp_var_value(Var.Bsp)
        self.assertEqual(value, 10.4)

    def test_set_and_get_exp_user_var_name(self):
        self.expedition.set_exp_user_var_name(Var.User0, "User Var 0")
        name = self.expedition.get_exp_var_name(Var.User0)
        self.assertEqual("User Var 0", name)

    def test_set_and_get_exp_vars(self):
        self.expedition.set_exp_vars([Var.User0, Var.User1, Var.User2], [0, 1, 2])
        values = self.expedition.get_exp_vars([Var.User0, Var.User1, Var.User2])
        self.assertEqual(values, [0, 1, 2])

    def test_get_sys_var(self):
        boat_length = self.expedition.get_sys_var(SysVar.BoatLength)
        if boat_length is not None:
            self.assertIsInstance(boat_length, float)

    @unittest.skipUnless(
        IS_WINDOWS and DLL_AVAILABLE,
        "Requires legacy ExpDLL with boat colour exports",
    )
    def test_set_and_get_boat_colour(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("GetBoatColour not exported on ExpDLL API 1.2")
        self.expedition.set_boat_colour(0, 0, 0, 0)
        colour = self.expedition.get_boat_colour(0)
        self.assertEqual(colour, (0, 0, 0))

    def test_set_and_get_boat_position(self):
        boat = 1
        self.expedition.set_boat_position(boat, (50.8, -1.3))
        position = self.expedition.get_boat_position(boat)
        self.assertEqual(position, (50.8, -1.3))

    def test_set_by_name(self):
        boat = 1
        self.expedition.set_exp_var_by_name("Lat", 50.7, boat)
        value = self.expedition.get_exp_var_value(Var.Lat, boat)
        self.assertEqual(value, 50.7)

    def test_set_by_name_error(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_by_name("Invalid", 50.7)

    def test_get_by_name(self):
        boat = 1
        self.expedition.set_exp_var_value(Var.Lon, -1.3, boat)
        value = self.expedition.get_exp_var_value_by_name("Lon", boat)
        self.assertEqual(value, -1.3)

    def test_set_dict(self):
        boat = 1
        self.expedition.set_exp_vars_dict({Var.Lat: 50.8, Var.Lon: -1.4}, boat)
        lat = self.expedition.get_exp_var_value(Var.Lat, boat)
        lon = self.expedition.get_exp_var_value(Var.Lon, boat)
        self.assertEqual(lat, 50.8)
        self.assertEqual(lon, -1.4)

    def test_get_variation(self):
        variation = self.expedition.get_variation(50.8, -1.3)
        if variation is not None:
            self.assertIsInstance(variation, float)

    @unittest.skipUnless(
        IS_WINDOWS and DLL_AVAILABLE,
        "Requires legacy ExpDLL with var precision exports",
    )
    def test_set_and_get_var_precision(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("SetVarPrecision not exported on ExpDLL API 1.2")
        self.expedition.set_var_precision(Var.User0, 3)
        precision = self.expedition.get_var_precision(Var.User0)
        self.assertIsInstance(precision, int)
        self.assertEqual(precision, 3)

    @unittest.skipUnless(
        IS_WINDOWS and DLL_AVAILABLE,
        "Requires legacy ExpDLL with AIS CPA export",
    )
    def test_get_ais_dangerous_cpa_shape(self):
        if self.expedition.api_version != "legacy":
            self.skipTest("GetAisDangerousCPA not exported on ExpDLL API 1.2")
        dangerous, name = self.expedition.get_ais_dangerous_cpa()
        self.assertIsInstance(dangerous, bool)
        self.assertIsInstance(name, str)

    @unittest.skipUnless(
        IS_WINDOWS and DLL_AVAILABLE,
        "Requires ExpDLL API 1.2",
    )
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
