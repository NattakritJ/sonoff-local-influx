"""
Root-level conftest.py for the standalone daemon test suite.

Adds src/ to sys.path so daemon modules (config, extractor, writer, ewelink)
are importable without installation.
"""
import sys
import os

# Add src/ to PYTHONPATH so daemon modules are importable without installation
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
