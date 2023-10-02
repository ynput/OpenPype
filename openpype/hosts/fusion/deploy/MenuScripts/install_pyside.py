# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import importlib
from install_pip_package import pip_install
from openpype.hosts.fusion import FUSION_VERSIONS_DICT

try:
    from qtpy import API_NAME

    print(f"Qt binding: {API_NAME}")
    mod = importlib.import_module(API_NAME)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except Exception:
    fusion_version = int(app.Version)
    fusion_python_home, _ = FUSION_VERSIONS_DICT.get(fusion_version)
    fusion_python_home = os.environ.get(fusion_python_home)
    print("Assuming no Qt library is installed..")
    print("Installing PySide package for " f"{fusion_python_home}")
    pip_install("PySide6", fusion_python_home)
