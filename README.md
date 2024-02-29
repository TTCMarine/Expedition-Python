# Expedition

## Description

Expedition is a Python module for managing and manipulating expeditions. It provides a simple and intuitive API for creating, updating, and retrieving expedition data.

## Installation

To install the Expedition module, you can use pip:

```bash
pip install Expedition
```

## Usage
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
```