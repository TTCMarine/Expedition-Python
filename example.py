from Expedition import ExpeditionDLL, Var

expedition = ExpeditionDLL("C:\\Program Files\\Expedition\\Expedition")

expedition.set_exp_var_value(Var.Bsp, 10.4)
expedition.set_exp_user_var_name(Var.User1, "1234567890123456")
value = expedition.get_exp_var_value(Var.Bsp)
print(value)

# set start line ends
expedition.set_exp_var_value(Var.StartPortEndLat, 50.8)
expedition.set_exp_var_value(Var.StartPortEndLon, -1.4)
expedition.set_exp_var_value(Var.StartStrbEndLat, 50.8)
expedition.set_exp_var_value(Var.StartStrbEndLon, -1.41)
