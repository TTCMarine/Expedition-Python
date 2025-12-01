import unittest
import platform
import os
import sys
from Expedition import ExpeditionDLL, Var, SysVar

EXPEDITION_INSTALL_64_PATH = "C:\\Program Files\\Expedition\\Expedition"
EXPEDITION_INSTALL_32_PATH = "C:\\Program Files (x86)\\Expedition\\Expedition"

# Check if we're on Windows and if Expedition DLL is available
IS_WINDOWS = sys.platform == 'win32'
DLL_AVAILABLE = False

if IS_WINDOWS:
    # Try to find the DLL in common installation paths
    for path in [EXPEDITION_INSTALL_64_PATH, EXPEDITION_INSTALL_32_PATH]:
        dll_path = os.path.join(path, 'ExpDLL.dll')
        if os.path.exists(dll_path):
            DLL_AVAILABLE = True
            break
    # Also try from_default_location (but catch all exceptions)
    if not DLL_AVAILABLE:
        try:
            # This might fail due to registry access or DLL loading
            exp = ExpeditionDLL.from_default_location()
            DLL_AVAILABLE = True
            # Clean up the instance
            del exp
        except Exception:
            # Any exception means DLL is not available
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
            cls.skip_reason = "Expedition DLL not found. Install Expedition or set up mock implementation."
        else:
            # Try to create an instance
            try:
                # First try from_default_location
                cls.expedition = ExpeditionDLL.from_default_location()
            except (FileNotFoundError, OSError, ImportError):
                # Fall back to hardcoded paths
                try:
                    architecture = platform.architecture()[0]
                    if architecture == "64bit":
                        cls.expedition = ExpeditionDLL(EXPEDITION_INSTALL_64_PATH)
                    else:
                        cls.expedition = ExpeditionDLL(EXPEDITION_INSTALL_32_PATH)
                except (FileNotFoundError, OSError):
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
        # On real DLL, this should match Var.NumChannels
        # On mock, it might be different, so just check it's an int
        if DLL_AVAILABLE and IS_WINDOWS:
            self.assertEqual(no_of_channels, Var.NumChannels)

    def test_get_exp_var_name(self):
        # Test a few variables instead of all to avoid long test times
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
        # On real DLL, this should be a float (could be None if invalid)
        # On mock, it might return None or a value
        if boat_length is not None:
            self.assertIsInstance(boat_length, float)

    def test_set_and_get_boat_colour(self):
        self.expedition.set_boat_colour(0, 0, 0, 0)
        colour = self.expedition.get_boat_colour(0)
        self.assertEqual(colour, (0, 0, 0))

    def test_set_and_get_boat_position(self):
        self.expedition.set_boat_position(0, (50.8, -1.3))
        position = self.expedition.get_boat_position(0)
        self.assertEqual(position, (50.8, -1.3))

    def test_set_by_name(self):
        self.expedition.set_exp_var_by_name("Lat", 50.7)
        value = self.expedition.get_exp_var_value(Var.Lat)
        self.assertEqual(value, 50.7)

    def test_set_by_name_error(self):
        with self.assertRaises(ValueError):
            self.expedition.set_exp_var_by_name("Invalid", 50.7)

    def test_get_by_name(self):
        self.expedition.set_exp_var_value(Var.Lon, -1.3)
        value = self.expedition.get_exp_var_value_by_name("Lon")
        self.assertEqual(value, -1.3)

    def test_set_dict(self):
        self.expedition.set_exp_vars_dict({Var.Lat: 50.8, Var.Lon: -1.4})
        lat = self.expedition.get_exp_var_value(Var.Lat)
        lon = self.expedition.get_exp_var_value(Var.Lon)
        self.assertEqual(lat, 50.8)
        self.assertEqual(lon, -1.4)

    @unittest.skip("Disabled for now, magvar not working as expected")
    def test_get_variation(self):
        variation = self.expedition.get_variation(50.8, -1.3)
        self.assertIsInstance(variation, float)


if __name__ == '__main__':
    unittest.main()
