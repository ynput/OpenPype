# -*- coding: utf-8 -*-
"""Setup info for building Pype 3.0."""
import os
import sys

from cx_Freeze import setup, Executable
from sphinx.setup_command import BuildDoc

version = {}
with open(os.path.join("pype", "version.py")) as fp:
    exec(fp.read(), version)
__version__ = version["__version__"]

base = None
if sys.platform == "win32":
    base = "Win32GUI"

# -----------------------------------------------------------------------
# build_exe
# Build options for cx_Freeze. Manually add/exclude packages and binaries

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
    "pynput",
    "jinxed",
    "blessed",
    "Qt",
    "speedcopy",
    "googleapiclient",
    "httplib2"
]

includes = [
    "repos/acre/acre",
    "repos/avalon-core/avalon",
    "repos/pyblish-base/pyblish",
    "repos/maya-look-assigner/mayalookassigner"
]

excludes = []
bin_includes = []
include_files = [
    "igniter",
    "pype",
    "repos",
    "schema",
    "setup",
    "vendor",
    "LICENSE",
    "README.md",
    "pype/version.py"
]

if sys.platform == "win32":
    install_requires.append("win32ctypes")

buildOptions = dict(
    packages=install_requires,
    includes=includes,
    excludes=excludes,
    bin_includes=bin_includes,
    include_files=include_files
)


executables = [
    Executable("start.py", base=None, targetName="pype_console"),
    Executable("start.py", base=base, targetName="pype")
]

setup(
    name="pype",
    version=__version__,
    description="Ultimate pipeline",
    cmdclass={"build_sphinx": BuildDoc},
    options={
        "build_exe": buildOptions,
        "build_sphinx": {
            "project": "Pype",
            "version": __version__,
            "release": __version__,
            "source_dir": "./docs/source",
            "build_dir": "./docs/build"
        }
    },
    executables=executables
)
