# Expedition-Python

## Description

Expedition is a Windows-based software application for sailing navigation and racing. It has been used in multiple Volvo
Ocean Race, America's Cup and Grand Prix events and is the most advanced and usable software available. It can be
purchased from [Expedition Marine](https://www.expeditionmarine.com/).

This Expedition-Python library is a module for reading and writing data from Expedition. It provides a simple and
intuitive API for reading and writing variables and system variables in Expedition. You can also do basic route and
waypoint manipulation.

## Installation

To install the Expedition module, you can use pip:

```bash
pip install Expedition-Python
```

## Usage

There is a static method called `from_default_location` that can be used to create an instance of the ExpeditionDLL
class.
This method will attempt to locate the Expedition DLL file and create an instance of the ExpeditionDLL. This relies on
the installation directory being in a registry key, so it may not work for all installations.

> **_Note on 64 vs 32-bit:_**
> If you are using a 32-bit version of Expedition, then you need to use a 32-bit version of Python.

Here's a simple example of how to use the Expedition module:

```python
from Expedition import ExpeditionDLL, Var, SysVar

# Create an instance of the ExpeditionDLL class
expedition = ExpeditionDLL.from_default_location()

# Set and get a variable value
expedition.set_exp_var_value(Var.Bsp, 10.4)
value = expedition.get_exp_var_value(Var.Bsp)
print(value)  # Outputs: 10.4
```

## Contributing

If you would like to contribute to the Expedition module, please submit a pull request.

## Tests

To run the tests for the Expedition module, you can use the following command:

```bash
python -m unittest discover tests
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
