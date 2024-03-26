import unittest
import platform
from Expedition import ExpeditionDLL, Var, SysVar

EXPEDITION_INSTALL_64_PATH = "C:\\Program Files\\Expedition\\Expedition"
EXPEDITION_INSTALL_32_PATH = "C:\\Program Files (x86)\\Expedition\\Expedition4D"


class TestExpedition(unittest.TestCase):
    def setUp(self):
        architecture = platform.architecture()[0]
        if architecture == "64bit":
            self.expedition = ExpeditionDLL(EXPEDITION_INSTALL_64_PATH)
        else:
            self.expedition = ExpeditionDLL(EXPEDITION_INSTALL_32_PATH)

    def test_number_of_vars(self):
        no_of_channels = self.expedition.number_of_vars
        self.assertIsInstance(no_of_channels, int)

    def test_get_exp_var_name(self):
        for i in range(self.expedition.number_of_vars):
            var_name = self.expedition.get_exp_var_name(i)
            self.assertIsInstance(var_name, str)

    def test_set_and_get_exp_var_value(self):
        self.expedition.set_exp_var_value(Var.Bsp, 10.4)
        value = self.expedition.get_exp_var_value(Var.Bsp)
        self.assertEqual(value, 10.4)

    def test_set_and_get_exp_user_var_name(self):
        self.expedition.set_exp_user_var_name(Var.User0, "User Var 0")
        name = self.expedition.get_exp_var_name(Var.User0)
        self.assertEqual(name, "User Var 0")

    def test_set_and_get_exp_vars(self):
        self.expedition.set_exp_vars([Var.User0, Var.User1, Var.User2], [0, 1, 2])
        values = self.expedition.get_exp_vars([Var.User0, Var.User1, Var.User2])
        self.assertEqual(values, [0, 1, 2])

    def test_get_sys_var(self):
        boat_length = self.expedition.get_sys_var(SysVar.BoatLength)
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


if __name__ == '__main__':
    unittest.main()
