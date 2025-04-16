Usage
=====

Here's a basic example of how to use Expedition-Python:

.. code-block:: python

   from Expedition import ExpeditionDLL, Var, SysVar

    # Create an instance of the ExpeditionDLL class
    expedition = ExpeditionDLL.from_default_location()

    # Set and get a variable value
    expedition.set_exp_var_value(Var.Bsp, 10.4)
    value = expedition.get_exp_var_value(Var.Bsp)
    print(value)  # Outputs: 10.4

