from Expedition import ExpeditionDLL, Var

expedition = ExpeditionDLL("C:\\Program Files\\Expedition\\Expedition")

expedition.set_exp_var_value(Var.Bsp, 10.4)
expedition.set_exp_user_var_name(Var.User1, "1234567890123456")
value = expedition.get_exp_var_value(Var.Bsp)
print(value)

expedition.set_boat_position(0, (50.8, -1.4))
position = expedition.get_boat_position(0)
print(position)

expedition.ping_mark("Test", 50.8, -1.4, True)

variation = expedition.get_variation(50.8, -1.4)
print(variation)