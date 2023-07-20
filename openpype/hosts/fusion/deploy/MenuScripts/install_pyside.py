# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import sys
import subprocess
import importlib
import platform
from install_pip_package import pip_install
from openpype.hosts.fusion import FUSION_VERSIONS_DICT


def get_pyside_version() -> str:
    os_platform = platform.system()
    pyside_version = "PySide2"
    if os_platform == "Darwin":
        pyside_version = "PySide6"
    return pyside_version


try:
    from qtpy import API_NAME

    print(f"Qt binding: {API_NAME}")
    mod = importlib.import_module(API_NAME)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except Exception:
    fusion_version = int(app.Version)
    fusion_python_home, _ = FUSION_VERSIONS_DICT.get(fusion_version)
    print("Assuming no Qt library is installed..")
    print("Installing PySide package for " f"{os.environ.get(fusion_python_home)}")
    pyside_version = get_pyside_version()
    pip_install(pyside_version, fusion_python_home)
