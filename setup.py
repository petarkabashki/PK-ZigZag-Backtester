# setup.py
# Build script for C extension modules using setuptools

from setuptools import setup, Extension
import numpy as np
import sys

# Define the extension modules
# Ensure source file paths are relative to this setup.py file
zigzag_module = Extension(
    'lib.zigzag', # Module name when imported in Python (use dot notation for package structure)
    sources=['lib/zigzag.c'],
    include_dirs=[np.get_include(), sys.prefix + '/include'], # Include NumPy and Python headers
    extra_compile_args=['-O2'], # Optional optimization flags
    language='c'
)

position_tools_module = Extension(
    'lib.position_tools', # Module name when imported
    sources=['lib/enumerate_trades.c'],
    include_dirs=[np.get_include(), sys.prefix + '/include'], # Include NumPy and Python headers
    extra_compile_args=['-O2'],
    language='c'
)

setup(
    name='PKZigZagBacktesterExtensions',
    version='0.1',
    description='C extensions for ZigZag calculation and trade enumeration',
    ext_modules=[zigzag_module, position_tools_module],
    # Specify the package directory so setuptools knows where 'lib' is
    package_dir={'': '.'},
    packages=['lib'] # Treat 'lib' as a package
)

# Command to build:
# python setup.py build_ext --inplace