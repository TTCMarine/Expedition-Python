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

Strict mode
-----------

By default, writes that Expedition ignores fail silently, as they do in the DLL. Pass
``strict=True`` while developing to raise instead:

.. code-block:: python

   from Expedition import ExpeditionDLL, ExpeditionNotRunningError, ExpeditionWriteError

   expedition = ExpeditionDLL.from_default_location(strict=True)
   try:
       expedition.set_exp_var_value(Var.Bsp, 10.4)
   except ExpeditionNotRunningError:
       ...  # Expedition is not running
   except ExpeditionWriteError:
       ...  # the value did not read back

Strict mode adds a running check before each write and a read-back after each write.

