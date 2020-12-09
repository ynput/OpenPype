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
    "win32ctypes"
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
