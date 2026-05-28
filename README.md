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

### Development Installation

For development, use [uv](https://docs.astral.sh/uv/) to create a virtual environment and install the package in editable mode with dev tools:

```bash
git clone https://github.com/TTCMarine/Expedition-Python.git
cd Expedition-Python
uv sync
```

Alternatively, you can use pip: `pip install -e .`

### Platform Support

- **Windows**: Full support with the Expedition DLL
- **macOS/Linux**: Mock implementation available for development and testing (see note below)

> **Note for macOS/Linux users:** On non-Windows platforms, the package installs a mock implementation that allows you to develop and test code without the actual Expedition DLL. All methods are available but return dummy values. This is useful for developing code that will run on Windows.

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

Contributions are welcome! If you would like to contribute to the Expedition module:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests to ensure everything works
5. Commit your changes (`git commit -m 'Add some amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

Please ensure your code follows the project's style guidelines and includes tests for new features.

## Development

### Requirements

- Python 3.8 or higher (3.12 recommended for local development; see `.python-version`)
- [uv](https://docs.astral.sh/uv/) for development (optional but recommended)
- For Windows: Expedition software installed

### Expedition API headers (local only)

Expedition’s C headers (`ExpDLL.h`, `user_channels.h`, `sys_channels.h`) are **proprietary** and are not committed or shipped with this package. On Windows, after installing or updating Expedition, sync them for local development and AI-assisted binding work:

```bash
uv run python scripts/sync_expedition_headers.py
uv run python scripts/generate_enums_from_headers.py --write
uv run python scripts/check_enums_against_headers.py
```

Headers are copied to `reference/expedition/` (gitignored). Enums in [`Expedition/enums.py`](Expedition/enums.py) are generated from those headers (see [`CHANGELOG.md`](CHANGELOG.md) for 2.0 breaking renames). See [`reference/README.md`](reference/README.md) and [`AGENTS.md`](AGENTS.md).

### Running Tests

After `uv sync`, run tests with:

```bash
uv run pytest tests/ -v
```

You can also use unittest: `python -m unittest discover tests`

> **Note:** Tests require the Expedition DLL to be installed on Windows. On non-Windows platforms or when the DLL is not found, tests will be automatically skipped. This is expected behavior and allows the test suite to run on CI/CD systems without Expedition installed.

### Building the Package

The package uses modern Python packaging with `pyproject.toml`. To build:

```bash
uv build
```

This will create distribution files in the `dist/` directory.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
