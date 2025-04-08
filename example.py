from Expedition import ExpeditionDLL, Var, SysVar

expedition = ExpeditionDLL("C:\\Program Files\\Expedition\\Expedition")

expedition.set_exp_var_value(Var.Bsp, 10.4)
expedition.set_exp_user_var_name(Var.User1, "1234567890123456")
value = expedition.get_exp_var_value(Var.Bsp)
print(value)
