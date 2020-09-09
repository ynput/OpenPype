# -*- coding: utf-8 -*-
"""Setup info for building Pype 3.0."""
import sys
from cx_Freeze import setup, Executable
from version import __version__


install_requires = ['clique',
                    'jsonschema',
                    'OpenTimelineIO',
                    'pathlib2',
                    'PIL',
                    'pymongo',
                    'Qt',
                    'speedcopy']

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

# Build options for cx_Freeze. Manually add/exclude packages and binaries
buildOptions = dict(
    packages=install_requires,
    excludes=[],
    bin_includes=[],
    include_files=['schema', 'setup', 'vendor']
)


executables = [
    Executable(
        'pype.py',
        base=None,
        targetName='pype'
    )
]

setup(
    name='pype',
    version=__version__,
    description='Ultimate pipeline',
    options=dict(build_exe=buildOptions),
    executables=executables,
)
