# -*- coding: utf-8 -*-
"""Setup info for building Pype 3.0."""
import sys
import os
from cx_Freeze import setup, Executable

version = {}
with open(os.path.join("pype", "version.py")) as fp:
    exec(fp.read(), version)
__version__ = version['__version__']


install_requires = [
    "appdirs",
    "cx_Freeze",
    "keyring",
    "clique",
    "jsonschema",
    "OpenTimelineIO",
    "pathlib2",
    "PIL",
    "pymongo",
    "Qt",
    "speedcopy"
]

base = None
if sys.platform == "win32":
    base = "Win32GUI"

# Build options for cx_Freeze. Manually add/exclude packages and binaries
buildOptions = dict(
    packages=install_requires,
    includes=[
        'repos/acre/acre',
        'repos/avalon-core/avalon',
        'repos/pyblish-base/pyblish',
        'repos/maya-look-assigner/mayalookassigner'
    ],
    excludes=[],
    bin_includes=[],
    include_files=[
        "pype",
        "repos",
        "schema",
        "setup",
        "vendor",
        "LICENSE",
        "README.md",
        "pype/version.py"]
)


executables = [Executable("pype.py", base=None, targetName="pype")]

setup(
    name="pype",
    version=__version__,
    description="Ultimate pipeline",
    options=dict(build_exe=buildOptions),
    executables=executables
)
