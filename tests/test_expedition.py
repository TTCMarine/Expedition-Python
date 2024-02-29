import unittest
from Expedition import ExpeditionDLL, Var, SysVar


class TestExpedition(unittest.TestCase):
    def setUp(self):
        self.expedition = ExpeditionDLL.from_default_location()

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


if __name__ == '__main__':
    unittest.main()
