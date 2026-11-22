Installation
============

You can install Expedition-Python via pip:

.. code-block:: bash

   pip install Expedition-Python

Requirements
------------

- Windows with Expedition installed, for real DLL use. macOS and Linux can import the package and use the ``Expedition.protocol`` module, but cannot load ExpDLL.
- Python 3.10+ with the same architecture as the Expedition build you use: AMD64 Python for `ExpeditionX64`, native ARM64 Python for `ExpeditionARM`. 32-bit Python cannot load either build.
- No runtime dependencies. All dependencies are installed automatically.
