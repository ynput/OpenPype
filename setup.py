# -*- coding: utf-8 -*-
"""Setup info for building Pype 3.0."""
import sys
import os
from cx_Freeze import setup, Executable
from sphinx.setup_command import BuildDoc

version = {}
with open(os.path.join("pype", "version.py")) as fp:
    exec(fp.read(), version)
__version__ = version['__version__']

includes = []
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
    "speedcopy",
]

base = None
if sys.platform == "win32":
    base = "Win32GUI"
    includes.append("pynput._util.win32")
    includes.append("pynput._util.win32_vks")
    includes.append("pynput.mouse._win32")
    includes.append("pynput.keyboard._win32")
    includes.append("jinxed.terminfo.vtwin10")
    # ----------------
    install_requires.append("win32ctypes")

elif sys.platform == 'darwin':
    includes.append("pynput._util.darwin")
    includes.append("pynput.mouse._darwin")
    includes.append("pynput.keyboard._darwin")

else:
    includes.append("pynput._util.xorg")
    includes.append("pynput.mouse._xorg")
    includes.append("pynput.keyboard._xorg")

# Build options for cx_Freeze. Manually add/exclude packages and binaries
buildOptions = dict(
    packages=install_requires,
    includes=includes,
    excludes=[],
    bin_includes=[],
    include_files=[
        "igniter",
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
