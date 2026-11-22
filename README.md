# Expedition-Python

[![Tests](https://github.com/TTCMarine/Expedition-Python/actions/workflows/test.yml/badge.svg)](https://github.com/TTCMarine/Expedition-Python/actions/workflows/test.yml)
[![Publish](https://github.com/TTCMarine/Expedition-Python/actions/workflows/publish.yml/badge.svg)](https://github.com/TTCMarine/Expedition-Python/actions/workflows/publish.yml)
[![Versioning](https://github.com/TTCMarine/Expedition-Python/actions/workflows/version.yml/badge.svg)](https://github.com/TTCMarine/Expedition-Python/actions/workflows/version.yml)
[![Coverage](https://codecov.io/gh/TTCMarine/Expedition-Python/branch/main/graph/badge.svg)](https://codecov.io/gh/TTCMarine/Expedition-Python)
[![PyPI version](https://img.shields.io/pypi/v/Expedition-Python)](https://pypi.org/project/Expedition-Python/)
[![Python versions](https://img.shields.io/pypi/pyversions/Expedition-Python)](https://pypi.org/project/Expedition-Python/)
[![License](https://img.shields.io/github/license/TTCMarine/Expedition-Python)](https://github.com/TTCMarine/Expedition-Python/blob/main/LICENSE)

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

- **Windows**: Full support. `ExpeditionDLL` loads the Expedition DLL.
- **macOS/Linux**: The `Expedition.protocol` module works, for building and checking Expedition's simple-protocol messages. `ExpeditionDLL` cannot load ExpDLL here, so DLL code has to run on Windows.

> **Note for macOS/Linux users:** The package has no mock DLL. The test suite uses a fake ExpDLL in `tests/fake_expdll.py`, which is a test helper and is not installed with the package. The unit tests for it and for `Expedition.protocol` run on any platform.

## Simple protocol

`Expedition.protocol` builds and checks Expedition's text-based simple protocol. It does no I/O, so you send the bytes over your own socket:

```python
from Expedition import protocol

packet = protocol.gun_set(12.34)  # b"#G,12.34*62\r\n"
# sock.sendall(packet); reply = sock.recv(256)
assert protocol.is_ack(reply, packet)
```

It covers the gun, start line, marks, routes, events, sails and system commands. See [docs/protocol.rst](docs/protocol.rst) for the full list, the limits and the Expedition settings the protocol needs.

## Usage

There is a static method called `from_default_location` that can be used to create an instance of the ExpeditionDLL
class.
This method will attempt to locate the Expedition DLL file and create an instance of the ExpeditionDLL. This relies on
the installation directory being in a registry key, so it may not work for all installations.

> **_Architecture must match:_**
> Expedition ships two builds. `ExpeditionARM/` contains an ARM64 `ExpDLL.dll` and needs native ARM64 Python.
> `ExpeditionX64/` contains an AMD64 `ExpDLL.dll` and needs AMD64 Python (which runs under emulation on ARM64 Windows).
> Native ARM64 Python for Windows is, as far as we know, only published from Python 3.11, so use 3.11 or later for
> `ExpeditionARM`. This has not been checked on a Windows machine yet.
> 32-bit Python cannot load either build. Expedition-Python checks the DLL's machine type against the interpreter before
> loading and raises `ExpeditionLoadError` with a message naming the mismatch.
>
> `from_default_location()` uses the registry, which points at whichever build was registered last. If both builds are
> installed, pass the build folder explicitly: `ExpeditionDLL(r"C:\Program Files\Expedition\ExpeditionARM")`.

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

### Strict mode

By default, writes that Expedition ignores fail silently, as they do in the DLL. Pass `strict=True` while developing to
find them:

```python
from Expedition import ExpeditionDLL, ExpeditionNotRunningError, ExpeditionWriteError, Var

expedition = ExpeditionDLL.from_default_location(strict=True)
try:
    expedition.set_exp_var_value(Var.Bsp, 10.4)
except ExpeditionNotRunningError:
    print("Start Expedition first")
except ExpeditionWriteError as err:
    print(f"Expedition did not apply the value: {err}")
```

Strict mode checks that Expedition is running before each write and reads each value back afterwards. It adds DLL calls,
so leave it off in production.

Other behaviour to know about:

- Bad arguments (channel IDs out of range for the loaded DLL, boat numbers outside `0..get_number_of_boats()-1`, unknown
  channel names, user variable names longer than 15 bytes) raise `ValueError` before anything reaches the DLL.
- Writes to boat 0 for GPS-derived channels (`Lat`, `Lon`, `Cog`, `Sog`, `GpsTime` and others) emit an
  `ExpeditionWriteWarning`. Expedition drops them unless the GPS source is set to the DLL.
- `get_exp_var_ex()` returns the value and the channel that supplied it, which matters for `Alt0`..`Alt9`.
- `is_running()` is a best-effort check based on `Var.Utc`.

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

- Python 3.10 or higher (3.12 recommended for local development; see `.python-version`)
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

The wrapper supports both legacy ExpDLL and Expedition **API 1.2** (ExpeditionX): batch var helpers fall back to single-var calls when needed; auxiliary APIs such as boat colour, marks, and AIS CPA require a legacy DLL.

### Running Tests

After `uv sync`, run tests with:

```bash
uv run pytest tests/ -v
```

Integration tests in `tests/test_expedition.py` need Expedition running on Windows. They skip otherwise. To point them at a
specific build, set `EXPEDITION_DLL_DIR` to its folder (for example `ExpeditionX64`). The unit tests fake the DLL and
run on any platform, including the `windows-11-arm` CI job.

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
