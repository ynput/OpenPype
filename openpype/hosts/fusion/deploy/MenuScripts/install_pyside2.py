# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import sys
import subprocess
import importlib


try:
    from qtpy import API_NAME

    print(f"Qt binding: {API_NAME}")
    mod = importlib.import_module(API_NAME)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except Exception:
    python_path = sys.base_prefix
    if python_path is None:
        print("Can't find any python environment.")

    print("Assuming no Qt library is installed..")
    print(f"Installing PySide2 for Python: {python_path}")

    # Get full path to python executable
    exe = "python.exe" if os.name == "nt" else "python"
    python = os.path.join(python_path, exe)
    assert os.path.exists(python), f"Python doesn't exist: {python}"

    # Do python -m pip install PySide2
    args = [python, "-m", "pip", "install", "PySide2"]
    print(f"Args: {args}")
    subprocess.Popen(args)
