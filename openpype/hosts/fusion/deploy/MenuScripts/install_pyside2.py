# This is just a quick hack for users running Py3 locally but having no
# Qt library installed
import os
import subprocess
import importlib


try:
    from qtpy import API_NAME

    print(f"Qt binding: {API_NAME}")
    mod = importlib.import_module(API_NAME)
    print(f"Qt path: {mod.__file__}")
    print("Qt library found, nothing to do..")

except ImportError:
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
