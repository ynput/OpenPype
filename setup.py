# -*- coding: utf-8 -*-
"""Setup info for building Pype 3.0."""
import os
import sys
import re
from pathlib import Path

from cx_Freeze import setup, Executable
from sphinx.setup_command import BuildDoc

version = {}

openpype_root = Path(os.path.dirname(__file__))

with open(openpype_root / "pype" / "version.py") as fp:
    exec(fp.read(), version)

version_match = re.search(r"(\d+\.\d+.\d+).*", version["__version__"])
__version__ = version_match.group(1)

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
    "opentimelineio",
    "pathlib2",
    "pkg_resources",
    "PIL",
    "pymongo",
    "pynput",
    "jinxed",
    "blessed",
    "Qt",
    "speedcopy",
    "googleapiclient",
    "httplib2",
    # Harmony implementation
    "filecmp"
]

includes = []
excludes = []
bin_includes = []
include_files = [
    "igniter",
    "openpype",
    "repos",
    "schema",
    "vendor",
    "LICENSE",
    "README.md"
]

if sys.platform == "win32":
    install_requires.extend([
        # `pywin32` packages
        "win32ctypes",
        "win32comext",
        "pythoncom"
    ])

build_options = dict(
    packages=install_requires,
    includes=includes,
    excludes=excludes,
    bin_includes=bin_includes,
    include_files=include_files,
    optimize=0
)

icon_path = openpype_root / "igniter" / "pype.ico"

executables = [
    Executable("start.py", base=None,
               target_name="openpype_console", icon=icon_path.as_posix()),
    Executable("start.py", base=base,
               target_name="openpype_gui", icon=icon_path.as_posix())
]

setup(
    name="OpenPype",
    version=__version__,
    description="Ultimate pipeline",
    cmdclass={"build_sphinx": BuildDoc},
    options={
        "build_exe": build_options,
        "build_sphinx": {
            "project": "OpenPype",
            "version": __version__,
            "release": __version__,
            "source_dir": (openpype_root / "docs" / "source").as_posix(),
            "build_dir": (openpype_root / "docs" / "build").as_posix()
        }
    },
    executables=executables
)
