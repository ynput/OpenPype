# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import subprocess
import importlib


try:
    from Qt import QtWidgets
    from Qt import __binding__
    print(f"Qt binding: {__binding__}")
    mod = importlib.import_module(__binding__)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except ImportError as exc:
    print("Assuming no Qt library is installed..")
    print('Installing PySide2 for Python 3.6: '
          f'{os.environ["FUSION16_PYTHON36_HOME"]}')

    # Get full path to python executable
    exe = "python.exe" if os.name == 'nt' else "python"
    python = os.path.join(os.environ["FUSION16_PYTHON36_HOME"], exe)
    assert os.path.exists(python), f"Python doesn't exist: {python}"

    # Do python -m pip install PySide2
    args = [python, "-m", "pip", "install", "PySide2"]
    print(f"Args: {args}")
    subprocess.Popen(args)
