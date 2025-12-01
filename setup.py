"""
Minimal setup.py for backward compatibility.

The actual package configuration is in pyproject.toml.
This file is kept for backward compatibility with older tools that may
expect setup.py. All package metadata is defined in pyproject.toml.

This file can be removed in the future as modern setuptools will use pyproject.toml.
"""
from setuptools import setup

# All configuration is in pyproject.toml
# Version is read dynamically from Expedition.__version__
setup()
