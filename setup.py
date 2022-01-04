# -*- coding: utf-8 -*-
"""Setup info for building OpenPype 3.0."""
import os
import sys
import re
import platform
from pathlib import Path

from cx_Freeze import setup, Executable
from sphinx.setup_command import BuildDoc

version = {}

openpype_root = Path(os.path.dirname(__file__))

with open(openpype_root / "openpype" / "version.py") as fp:
    exec(fp.read(), version)

version_match = re.search(r"(\d+\.\d+.\d+).*", version["__version__"])
__version__ = version_match.group(1)

low_platform_name = platform.system().lower()
IS_WINDOWS = low_platform_name == "windows"
IS_LINUX = low_platform_name == "linux"
IS_MACOS = low_platform_name == "darwin"

base = None
if IS_WINDOWS:
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
    "filecmp",
    "dns",
    # Python defaults (cx_Freeze skip them by default)
    "dbm",
    "sqlite3"
]

includes = []
# WARNING: As of cx_freeze there is a bug?
# when this is empty, its hooks will not kick in
# and won't clean platform irrelevant modules
# like dbm mentioned above.
excludes = [
    "openpype"
]
bin_includes = [
    "vendor"
]
include_files = [
    "igniter",
    "openpype",
    "repos",
    "schema",
    "LICENSE",
    "README.md"
]

if IS_WINDOWS:
    install_requires.extend([
        # `pywin32` packages
        "win32ctypes",
        "win32comext",
        "pythoncom"
    ])


icon_path = openpype_root / "igniter" / "openpype.ico"
mac_icon_path = openpype_root / "igniter" / "openpype.icns"

build_exe_options = dict(
    packages=install_requires,
    includes=includes,
    excludes=excludes,
    bin_includes=bin_includes,
    include_files=include_files,
    optimize=0
)

bdist_mac_options = dict(
    bundle_name="OpenPype",
    iconfile=mac_icon_path
)

executables = [
    Executable("start.py", base=base,
               target_name="openpype_gui", icon=icon_path.as_posix()),
    Executable("start.py", base=None,
               target_name="openpype_console", icon=icon_path.as_posix())
]
if IS_LINUX:
    executables.append(
        Executable(
            "app_launcher.py",
            base=None,
            target_name="app_launcher",
            icon=icon_path.as_posix()
        )
    )

setup(
    name="OpenPype",
    version=__version__,
    description="OpenPype",
    cmdclass={"build_sphinx": BuildDoc},
    options={
        "build_exe": build_exe_options,
        "bdist_mac": bdist_mac_options,
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
